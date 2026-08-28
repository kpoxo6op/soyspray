# Vaultwarden role defaults

[`main.yml`](main.yml) defines four inputs:

- `vaultwarden_enabled` controls the application lifecycle.
- `vaultwarden_target_revision` selects the pushed Git revision for Argo CD.
- `vaultwarden_account_email_override` updates the shared account email in the
  bootstrap Secret after a coordinated account email change.
- `vaultwarden_agent_master_password_override` updates the bootstrap Secret
  during a coordinated account password change.

Pass overrides through a protected runtime variables file. Do not put the
account email, password, or variables file in Git or a shell argument.
