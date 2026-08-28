# Vaultwarden role tasks

[`main.yml`](main.yml) selects the lifecycle path.
[`enabled.yml`](enabled.yml) applies the Argo CD resources and creates or reuses
the dedicated automation login in `vaultwarden-agent-login`. It also removes
the old shared-account Secret.
[`disabled.yml`](disabled.yml) removes the Argo CD resources while it keeps the
agent login Secret and retained PVC.
