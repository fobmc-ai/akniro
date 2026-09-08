# Event Bus

Events are immutable facts with event ID, type, schema version, subject, source, correlation ID, causation ID, timestamp, sequence, tenant/site scope, and payload. Consumers must be idempotent. Delivery is at-least-once unless a contract explicitly states otherwise.

Commands express intent; events express facts. Do not use events as hidden commands.

