# Resource Manager

Resource Manager owns CPU affinity, realtime priority, memory, GPU/NPU, storage, network, camera, fieldbus NIC, USB, and serial leases. Critical control resources are reserved and preemptible only by declared safety policy.

AI and analytics MUST observe quotas and MUST NOT reclaim resources leased by Motion, EtherCAT, Safety, or PLC runtime.

