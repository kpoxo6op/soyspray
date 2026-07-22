# Soyspray

Soyspray is a three-node Kubernetes home lab built with Kubespray. Ansible
bootstraps the cluster and Argo CD owns its workloads.

## Start here

```sh
make setup
make check
```

Use `make help` for the short command list. Cluster-changing work flows through
Ansible and Argo CD rather than direct changes to live resources.

## Cluster services

| Surface | Address |
| --- | --- |
| Grafana | <https://grafana.soyspray.vip> |
| Argo CD | <https://argocd.soyspray.vip> |

The hostnames resolve on the home LAN and through its advertised Tailscale
route. Secrets and login details are not stored in this repository.

## Repository map

- [`kubespray/`](kubespray/) contains the pinned cluster provisioner.
- [`playbooks/`](playbooks/README.md) contains deployment and operations entry
  points.
- [`roles/`](roles/) contains reusable Ansible roles.
- [`scripts/`](scripts/README.md) contains validation and operator helpers.
- [`soydocs/`](soydocs/README.md) contains cluster build notes and maintenance
  records.

## Change rules

- Work on a branch and push it before deployment.
- Change the cluster through Ansible and Argo CD, not ad hoc `kubectl` writes.
- Run `make go` before deployment.
- Add tests and a rollback path for behaviour changes.

Reusable engineering workflows live under `.agents/skills`. They cover
Ansible application roles, Argo/Kubernetes architecture, lab UX, browser
testing, security, debugging, TDD, and completion verification.
