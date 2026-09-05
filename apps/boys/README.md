# Boys

Open <https://boys.soyspray.vip>. Use **Календарь** to mark free days and
**Ссылки** to keep accommodation links. Select an unclaimed name, enter the crew
PIN, then set a personal PIN. Claimed names require their personal PIN.

The app keeps the existing SQLite database, sessions, and single-writer
`boys` deployment on `boys-data`. The critical Longhorn backup group protects
that claim. See [recovery operations](../../playbooks/operations/recovery/README.md)
for isolated restores and their evidence limits.

Run these commands from the repository root:

```sh
make status APP=boys FORMAT=json
make check APP=boys
make diff APP=boys
make deploy APP=boys REVISION=YOUR_PUSHED_BRANCH
```

After merge, run `make deploy APP=boys`. Deployment uses the existing Ansible
path, including the full local gate and preflight. Source changes build a
separate immutable image; deploy its reviewed digest promotion to change the
running app.

Application adoption is pending. Source, manifests, browser checks, and the
[detailed operating guide](../../kubernetes/boys/README.md) still use
`kubernetes/boys/`. Keep the current runtime Secret and signing key. Moving
those files and bootstrap inputs is a separate change after recovery checks.
