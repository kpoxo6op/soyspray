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

After node maintenance, restore temporary application settings. Authentik's
normal worker disruption budget keeps one worker available; see its
[operations guide](https://github.com/kpoxo6op/soyspray/tree/main/apps/authentik).

The retained-OS node rejoin stops if the `cert-manager` namespace is
terminating. Resolve that separate namespace incident, then retry the same
idempotent operation. Node recovery does not remove application finalizers or
admission registrations.

## Detailed procedures

- [Native node drill v2](https://github.com/kpoxo6op/soyspray/tree/main/playbooks/operations/nodes/drill-v2):
  an experimental remove/readd exercise on node-2, then node-1. It records native
  failures and recovery, with an explicitly authorized disruptive fallback that
  can lose data. It uses existing backup restore tools and has not yet passed
  its live acceptance run. Ordinary maintenance does not imply this permission.
- [Application operations](https://github.com/kpoxo6op/soyspray/tree/main/apps)
- [Ansible operations](https://github.com/kpoxo6op/soyspray/tree/main/playbooks/operations)
- [Repository helper commands](https://github.com/kpoxo6op/soyspray/tree/main/scripts)
