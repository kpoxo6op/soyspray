# Vaultwarden role tasks

[`main.yml`](main.yml) selects the lifecycle path.
[`enabled.yml`](enabled.yml) applies the Argo CD resources and creates or reuses
the shared account login in the runtime bootstrap Secret.
[`disabled.yml`](disabled.yml) removes the Argo CD resources while it keeps the
bootstrap Secret and retained PVC.
