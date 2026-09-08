# Realtime Architecture

Realtime execution is isolated by process, scheduling policy, CPU/resource reservation, dependency policy, and deployment package boundary. Non-deterministic network, cloud, AI, browser, garbage-collection-sensitive, and unbounded storage operations are outside the realtime loop.

Failure behavior must be explicit: safe stop, hold, degraded operation, or operator intervention. Every runtime has health, watchdog, startup, shutdown, and recovery contracts.

