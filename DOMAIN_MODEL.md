# Domain Model

Canonical entities: Tenant, Site, Area, Cell, Machine, Machine Project, Device, Tag, Alarm, Recipe, Event, Workflow, Rule, Report, Dashboard, User, Agent, Deployment, Backup, Capability, Resource Lease.

Every entity has: immutable ID, tenant/site scope, schema version, lifecycle status, created/updated timestamps, owner, audit metadata, and optimistic concurrency token.

Derived views MUST identify their source and freshness. No application may create a second canonical representation of a core entity.

