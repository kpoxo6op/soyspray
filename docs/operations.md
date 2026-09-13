# Everyday operations

Start with the maintained repository commands. They read native Kubernetes and
Argo CD state and explain evidence gaps.

## Check the system

```sh
make apps
make status APP=boys FORMAT=json
make backup-status FORMAT=json
```

`make apps` lists applications and ownership. `make status` combines desired
source, live health, access, and recovery evidence for one application.
`make backup-status` reads native backup records and private restore reports.

## Change an application

1. Work on a branch.
2. Change the application folder and its technical README together.
3. Run the maintained application check and diff.
4. Open a pull request and wait for required checks.
5. Merge to `main`; Argo CD then follows the reviewed source.

Do not use ad hoc Kubernetes writes for a lasting change. A live application
must not be retargeted to a topic branch.

Node-0, node-1 and node-2 use one native Kubespray procedure: prepare survivor
access and backups, remove, readd, then verify recovery. All validation drills
are complete. Keep disruption budgets and storage policy in place; the guide
covers first-member discovery and node-0's local storage without extra wrappers.

## Detailed procedures

- [Native node removal and readd](https://github.com/kpoxo6op/soyspray/tree/main/playbooks/operations/nodes):
  the retained-OS Kubespray path for one target at a time. The disruptive
  fallback requires separate authorization and can lose data.
- [Application operations](https://github.com/kpoxo6op/soyspray/tree/main/apps)
- [Ansible operations](https://github.com/kpoxo6op/soyspray/tree/main/playbooks/operations)
- [Repository helper commands](https://github.com/kpoxo6op/soyspray/tree/main/scripts)
