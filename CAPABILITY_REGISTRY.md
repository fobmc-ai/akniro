# Capability Registry

Capabilities are machine-readable contracts such as `motion.axis.cia402`, `plc.online-monitor`, or `ai.engineering.context`. Each has ID, version, provider, prerequisites, lifecycle, license requirement, resource profile, and compatibility range.

Apps query capabilities through the registry. They MUST NOT detect functionality by file presence or vendor name.

