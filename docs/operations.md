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

## Detailed procedures

- [Application operations](https://github.com/kpoxo6op/soyspray/tree/main/apps)
- [Ansible operations](https://github.com/kpoxo6op/soyspray/tree/main/playbooks/operations)
- [Repository helper commands](https://github.com/kpoxo6op/soyspray/tree/main/scripts)
