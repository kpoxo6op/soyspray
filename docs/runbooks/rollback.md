# Roll back

Use Git and Argo CD for normal rollback. Do not delete live resources by hand.

1. Identify the last known good commit.
2. Revert the faulty change on the branch.
3. Run `make check`.
4. Push the revert.
5. Apply the Argo definitions through the standard Ansible playbook.
6. Wait for Argo to report `Synced` and `Healthy`.
7. Run `make status` and `make smoke`.

For a failed Kong release change, verify the proxy and Admin Services before
changing chart values again. For a route or plugin fault, compare the Argo diff
and the route annotations first.

Removing the whole lab is a separate destructive operation. It requires an
explicit plan that covers Argo finalizers, namespaces, load-balancer addresses,
DNS records, and retained Secrets.
