# AI Safety

AI workflow is Read → Suggest → Patch → Test → Apply → Deploy. Read and suggest may be automated within policy. Patch requires diff review. Apply requires tests and authorized human approval. Deploy is prohibited for PLC, Motion, EtherCAT, Safety, IO, and other critical changes without explicit human approval and runtime validation.

The PM Apply endpoint only accepts an authorized human actor with an approval ID, a same-project `VALIDATED` test Evidence, and an expected target revision. It refuses already-applied suggestions, cross-project targets, controlled release/deployment/asset objects, and patches containing force, deployment, approval, safety-override, or direct-deploy actions.

