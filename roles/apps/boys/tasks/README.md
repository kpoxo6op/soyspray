# Boys role tasks

The task dispatcher selects the enabled or disabled lifecycle. The enabled
path creates runtime secrets before Argo CD. The disabled path quiesces Argo CD
before it removes the workloads and secrets.
