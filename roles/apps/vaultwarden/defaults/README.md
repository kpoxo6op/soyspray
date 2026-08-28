# Vaultwarden role defaults

[`main.yml`](main.yml) defines four inputs:

- `vaultwarden_enabled` controls the application lifecycle.
- `vaultwarden_target_revision` selects the pushed Git revision for Argo CD.
- `vaultwarden_agent_email` is the fixed non-human account used by automation.
- `vaultwarden_agent_master_password_override` rotates that account's login
  Secret after a coordinated agent password change.

Pass overrides through a protected runtime variables file. Do not put the
agent password or variables file in Git or a shell argument. Human account
details are not role inputs.
