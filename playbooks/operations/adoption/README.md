# Main-only GitOps adoption

`main-only-gitops.yml` performs the one-time catalog adoption from a pushed
branch. Child Applications still follow `main`, so the operation changes their
ownership definitions without selecting branch workload content.

The operation requires the fixed root project permission and an exact root
source on `main`. It uses resource-version guards and waits for the pushed root
commit to become `Synced` and `Healthy`. Return the root to `main` with
`playbooks/bootstrap-apps.yml` after verification.
