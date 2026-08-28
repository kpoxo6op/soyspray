# Vaultwarden role defaults

[`main.yml`](main.yml) defines three inputs:

- `vaultwarden_enabled` controls the application lifecycle.
- `vaultwarden_target_revision` selects the pushed Git revision for Argo CD.
- `vaultwarden_agent_master_password_override` updates the bootstrap Secret
  during a coordinated account password change.

Pass a password override only through a protected runtime variables file. Do
not put it in Git or a shell argument.

