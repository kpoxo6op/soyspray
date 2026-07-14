# Runbooks

These pages contain short, repeatable operating procedures for the Kong lab.

| Runbook | Use |
| --- | --- |
| [`power.md`](power.md) | Switch the lab on or off |
| [`deploy.md`](deploy.md) | Apply GitOps application definitions |
| [`verify.md`](verify.md) | Check health and collect evidence |
| [`onboard-api.md`](onboard-api.md) | Add another synthetic API safely |
| [`rollback.md`](rollback.md) | Return to a known revision |

Commands that change application state flow through Ansible and Argo CD. The
verification commands are read-only.
