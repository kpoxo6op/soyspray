# Boys application role

This role creates the runtime-only secrets, applies the restricted Argo CD
project, and applies the boys Application. Set `boys_target_revision` to a
pushed topic branch for a pre-merge deployment.

Set `boys_enabled=false` to remove the workloads and secrets. The namespace and
`boys-data` claim use `Delete=false`, so this action keeps the saved names and
dates.
