# Soyspray

Soyspray is a three-node Kubernetes home lab built with Kubespray. Ansible
bootstraps the cluster and Argo CD owns its workloads.

The Kong Bank Lab runs a small banking API platform on that cluster. It has two
Kong OSS gateways, six mock banking APIs, synthetic customers, authentication,
rate limiting, network policies, and a Grafana operator dashboard. It uses only
synthetic data.

## Start here

```sh
make setup
make check
make status
```

Use `make help` for the short command list. The
[operator guide](https://banklab-docs.soyspray.vip) is published automatically
from [docs](docs/index.md). Run `make docs-serve` only when a local preview is
useful.

## Live lab

| Surface | Address |
| --- | --- |
| Customer app | <http://banklab-web.soyspray.vip> |
| Operator guide | <https://banklab-docs.soyspray.vip> |
| Grafana | <https://grafana.soyspray.vip> |
| Argo CD | <https://argocd.soyspray.vip> |

The hostnames resolve on the home LAN and through its advertised Tailscale
route. Secrets and login details are not stored in this repository.

## Change rules

- Work on a branch and push it before deployment.
- Change the cluster through Ansible and Argo CD, not ad hoc `kubectl` writes.
- Run `make go` before deployment.
- Keep Kong Admin API private.
- Add tests and a rollback path for behaviour changes.

Reusable engineering workflows live under `.agents/skills`. They cover
Ansible application roles, Argo/Kubernetes architecture, lab UX, browser
testing, security, debugging, TDD, and completion verification.

Cluster build notes and one-off maintenance records remain under
[soydocs](soydocs/README.md).
