# Playbooks

Kubespray owns the Kubernetes foundation. Argo CD owns application workloads.
The remaining Ansible playbooks have narrow purposes:

- `bootstrap-apps.yml` installs or repairs the fixed Argo root.
- `bootstrap-app-inputs.yml` creates private application inputs.
- `operations/` contains recovery, retirement, storage, node, and network work.
- `argocd/` contains older workload manifests and Argo configuration.

Normal application delivery does not run an Ansible playbook. Run the local
gate and merge the pull request to `main`:

```sh
make check APP=boys
make go
```

Use the app README for private-input, restore, and retirement commands. Never
use an operation playbook as a substitute for a Git change.
