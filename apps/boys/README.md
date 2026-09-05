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
those files is a separate change after recovery checks.

## Bootstrap and recovery inputs

Normal deployment uses the existing `boys-runtime` and
`boys-cloudflared-token` Secrets. It does not read `.env` for Boys or rewrite
those Secrets. A supplied value that differs from an existing identity stops
the operation before any write.

For recovery, create an Ansible Vault variables file outside the checkout.
Supply `boys_pin` as a quoted string, `boys_session_key` as the original signing
key, and `boys_cloudflared_token` as the existing tunnel token. Restore these
values from the off-cluster runtime archive. Do not generate replacements.
Keep the Vault password and an offline recovery copy outside the cluster.

Push the branch and run `make go`, then run:

```sh
source soyspray-venv/bin/activate
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu apps/boys/bootstrap.yml \
  --ask-vault-pass -e @/private/path/boys-runtime.vault.yml --check
```

Remove `--check` to restore missing identities, then use `make deploy APP=boys`.
The operation creates only missing Secrets. Native create rejects a competing
creation instead of overwriting it. Secret content uses standard input and
suppressed task output. No plaintext file is written on the node. Check mode
validates inputs and skips creation.

The separate [trip bootstrap](../../playbooks/operations/boys/README.md) loads
the private initial seed from encrypted input. It does not replace the current
trip database. Keep `boys-data`, the database path, and the session key together
through restores so existing dates, personal PIN hashes, and sessions survive.

## Check a restored data copy

`check_restore.py` checks a restored `boys.sqlite3` with its WAL files present.
It uses SQLite's backup API to make a second disposable database before starting
the app or testing claims. The supplied restore remains unchanged. The app binds
only to an ephemeral loopback port.

Give the checker `--database /private/restore/boys.sqlite3` and
`--runtime /private/copied-app`. The runtime directory must contain `/app` copied
from the selected deployed image. Pass a JSON object with `boys_pin` and
`boys_session_key` on standard input from the encrypted recovery archive. Keep
this transfer out of shell history and logs. The checker prints only counts,
check results, and evidence gaps, and returns a nonzero code on failure.

The checks cover SQLite integrity and foreign keys, unchanged records at startup,
authenticated calendar/history/trip reads, legacy session format, preserved PIN
hashes, and concurrent claims on the disposable copy. A fully claimed crew has no
unclaimed identity for the race check; this result remains unknown with its cause.
The checker does not guess a human PIN or claim that a saved browser cookie was
tested. It does not prove that the backup is recent or perform the volume restore.
Use the [isolated Longhorn restore operation](../../playbooks/operations/recovery/README.md#inspect-an-isolated-volume-restore)
for that step. Run `make check APP=boys` for synthetic recovery checks.
