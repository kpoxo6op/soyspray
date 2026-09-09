# Soyspray

Soyspray is a three-node Kubernetes home lab built with Kubespray. Ansible
bootstraps the cluster and Argo CD owns its workloads.

## Start here

```sh
make setup
make check
```

Use `make help` for the short command list. Merge reviewed application changes
to `main`. Argo CD then reconciles them. Use Ansible only for the cluster
foundation, private inputs, recovery, and deliberate retirement.

## Cluster services

| Surface | Address |
| --- | --- |
| Grafana | <https://grafana.soyspray.vip> |
| Argo CD | <https://argocd.soyspray.vip> |

The hostnames resolve on the home LAN and through its advertised Tailscale
route. Secrets and login details are not stored in this repository.

## Repository map

- [`kubespray/`](kubespray/) contains the pinned cluster provisioner.
- [`argocd/`](argocd) contains the complete application catalog.
- [`playbooks/`](playbooks) contains bootstrap and operations entry
  points.
- [`roles/`](roles/) contains reusable Ansible roles.
- [`scripts/`](scripts) contains validation and operator helpers.
- [`soydocs/`](soydocs) contains cluster build notes and maintenance
  records.

## Change rules

- Work on a branch. Merge through a GitHub pull request.
- Change the cluster through Ansible and Argo CD, not ad hoc `kubectl` writes.
- Run `make go` before merge.
- Add tests and a rollback path for behaviour changes.

The [two repo skills](.agents/skills) cover operating Soyspray and
changing an application. Shared laptop skills are maintained outside the repo.
