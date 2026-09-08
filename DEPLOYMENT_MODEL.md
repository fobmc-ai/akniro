# Deployment Model

Deployment flow: Build → Package → Sign → Validate → Stage → Deploy → Health Check → Commit. A failure triggers automatic rollback when safe. One Machine Project revision is the deployment unit; individual app downloads are not a substitute for coherent deployment.

