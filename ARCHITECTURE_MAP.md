# Architecture Map

```text
Hardware -> HAL/Drivers -> Realtime Runtime -> Core Domain -> Apps/Engineering
                                      |             |
                                      v             v
                                Data Plane     Control Plane
                                      |             |
                                Historian/Event -> Cloud Sync
                                      ^             ^
                                      |             |
                              AI Index/Context -> Governed Agents
```

## Ownership map

| Object | Canonical owner | Consumers |
|---|---|---|
| Machine Project | Project Service | IDE, deployment, AI, backup |
| Tag definition | Tag Registry | runtime, HMI, historian |
| Live tag value | Runtime/Data Plane | HMI, rules, historian |
| Device identity | Device Registry | drivers, runtime, apps |
| Alarm definition/state | Alarm Service | HMI, historian, reports |
| Recipe | Recipe Service | runtime, MES, HMI |
| Audit record | Audit Service | security, reports, AI governance |
| Capability | Capability Registry | apps, licensing, UI |
| Resource lease | Resource Manager | runtimes, schedulers |

## Boundary test

If a module needs another module's database tables, private files, or runtime memory, the boundary is broken. Use an API, event, or explicit shared schema instead.

