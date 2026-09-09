# Testing

Testing levels: schema/contract, unit, property, integration, simulation, realtime timing, hardware-in-loop, deployment/rollback, security, migration, and disaster recovery. Critical paths require deterministic evidence and traceability to IDs.

The repository quality gate runs the complete Python suite, validates the example Machine Project, and parses every inline Management Center script with `node tools/check_web_syntax.js`. Real PLC, Motion, Safety, EtherCAT, IO, and firmware deployment remain human-gated integration activities; software simulation and evidence are the automated pre-hardware boundary.

