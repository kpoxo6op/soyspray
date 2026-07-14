# Get started

## Local setup

You need Python 3.13, `kubectl`, `argocd`, and Ansible. The repository already
contains the Kubespray inventory and Ansible configuration.

```sh
make setup
make check
```

`make setup` creates `soyspray-venv` and installs the development dependencies.
`make check` stays local and does not change the cluster.

## Cluster access

`kubectl` should use the Soyspray context. Confirm it before running a read-only
check:

```sh
kubectl config current-context
kubectl get nodes
```

The expected nodes are `node-0`, `node-1`, and `node-2`. All three should be
`Ready`.

## Open the documentation

The published guide is at
[banklab-docs.soyspray.vip](https://banklab-docs.soyspray.vip).

For a local preview while editing:

```sh
make docs-serve
```

The preview runs at <http://127.0.0.1:8000>. The process stays in the foreground
and reloads when a Markdown or stylesheet file changes.

## Before a deployment

Commit and push the branch, then run:

```sh
make go
```

This runs the local gate, checks the working tree, confirms cluster access, and
shows the current Argo state. Follow the [deployment runbook](runbooks/deploy.md)
after it passes.
