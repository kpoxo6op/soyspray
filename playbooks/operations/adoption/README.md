# Main-only GitOps adoption

`main-only-gitops.yml` performs the one-time catalog adoption from a pushed
branch. Child Applications still follow `main`, so the operation changes their
ownership definitions without selecting branch workload content.

The operation requires the fixed root project permission and an exact root
source on `main` or the selected adoption branch. It uses resource-version
guards, supports a retry after an interrupted run, waits for the pushed root
commit to become `Synced` and `Healthy`, and removes legacy cascading-deletion
finalizers. Return the root to `main` with `playbooks/bootstrap-apps.yml` after
verification. Then run `return-root-to-main.yml` with the exact `main_commit`.
It removes only the temporary root tracking label from branch-only objects and
waits for the old `main` root to become clean. It does not remove those objects.
