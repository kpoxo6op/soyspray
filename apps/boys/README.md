# Boys

Open <https://boys.soyspray.vip>. Use **Календарь** to mark free days and
**Ссылки** to keep accommodation links. Select an unclaimed name, enter the crew
PIN, then set a personal PIN. Claimed names require their personal PIN.

**Календарь** opens first. Mark days or use **Выбрать диапазон**, then select
**Сохранить даты**. **Ссылки** keeps a separate list of manual accommodation
links. Failed saves retain the draft. Review conflicts before reapplying edits.
The save indicator remains visible on phones, and leaving with unsaved changes
gives a warning. General availability and earlier events remain available.
The smaller interface preserves existing hidden trip fields and audit history.

The app keeps the existing SQLite database, sessions, and single-writer
`boys` deployment on `boys-data`. The critical Longhorn backup group protects
that claim. See [recovery operations](../../playbooks/operations/recovery/README.md)
for isolated restores and their evidence limits.

Run these commands from the repository root:

```sh
make status APP=boys FORMAT=json
make check APP=boys
make diff APP=boys
make smoke APP=boys
make deploy APP=boys REVISION=YOUR_PUSHED_BRANCH
```

After merge, run `make deploy APP=boys`. Deployment uses the existing Ansible
path, including the full local gate and preflight. Source changes build a
separate immutable image; deploy its reviewed digest promotion to change the
running app.

The native root owns the existing Boys Application and AppProject. Their
prune and deletion guards preserve them if removed from the root. The namespace
and PVC also have explicit data protection. Normal deployment cannot retire
Boys or remove its access keys.

Runtime source and its compatibility contract are in [app/](app/README.md).
[manifests/](manifests/README.md) contains the workload and tunnel configuration.
Checks live in `tests/`. The Docker build includes only the listed runtime files;
Python and browser tools are development dependencies outside the image.
The image workflow checks fresh access, migration, and rollback with disposable
data before publishing. It opens a draft promotion and never merges or deploys.

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

## Run an isolated restore

```sh
make restore-check APP=boys
```

The command runs the full gate and preflight. It selects the newest completed
backup of the bound `boys-data` volume on `critical-s3`. It checks completion,
errors, and the snapshot start time, then uses the existing Ansible operations
to restore a separate volume. Source claim and backup UIDs must match before
restoration and cleanup.

Inputs default to `~/.config/soyspray/recovery/boys-runtime.vault.yml` and
`~/.config/soyspray/recovery/vault-password`. The archived PIN and signing key
must match the live identity. Set `ANSIBLE_VAULT_PASSWORD_FILE` for a different
password file. To select another encrypted file or completed backup, use
`python -m apps.boys.restore_check --vault-file /private/runtime.vault.yml
--backup backup-NAME` in the activated project venv. This path runs the same gate.

The command copies the entire restored directory, including SQLite WAL files,
and `/app` from the pinned running image into private temporary storage.
`check_restore.py` creates a second database with SQLite's backup API before
starting the app on loopback or testing claims. It checks integrity, saved dates,
history, trip data, legacy session format, and preserved PIN hashes. Personal-PIN
and saved-browser-cookie checks remain unknown; no PIN is guessed.

Cleanup removes only scratch resources with the selected backup UID, including
after a failed data check. A cleanup failure fails the operation and keeps its
cause in the report. Temporary local data and kubeconfig copies are removed.
Private logs and `report.json` remain under
`~/.local/state/soyspray/restores/boys/<check-id>/`, or under `XDG_STATE_HOME`.
Reports contain counts, resource identities, the image digest, recovery-point
age, and evidence gaps. They contain no private trip content or credentials.

A passed restore report proves that one selected backup passed these checks.
It does not prove seven days of recovery-point coverage. The command does not
change the live workload or its data. Use the report's check ID and backup UID
with the guarded [cleanup operation](../../playbooks/operations/recovery/README.md)
if an interrupted check leaves scratch resources behind.

`make status APP=boys FORMAT=json` and `make backup-status FORMAT=json` show
native backup age and the private restore reports available on this operator
machine. Reports must match the observed claim and PV UIDs. Status shows the
last attempt separately from the last accepted restore, including its age and
tested image. A later failure does not erase earlier evidence. Missing or
invalid reports remain unknown with a cause. These reports do not prove seven
days of backup coverage or an existing human browser login.

## Check the live public journey

`make smoke APP=boys` reads the access URL from Application metadata and opens
fresh phone and desktop browser contexts. It checks readiness, protected private
API routes, the absent public seed, and keyboard navigation from name selection
to the appropriate PIN screen. Browser writes and requests to other origins are
blocked. No PIN is entered, no identity is claimed, and no plan is changed.

The command prints JSON. A completed public check returns zero with overall
status `partial`; authenticated sign-in, claim completion, calendar saves, and
links remain unknown with a cause. A failed public check returns nonzero. If all
names are claimed or unclaimed, the unavailable counterpart screen is unknown.
No response bodies, screenshots, traces, cookies, or personal names are saved.
Use the installed app browser dependencies from `make setup`. The existing local
and image tests verify writes and claim races against disposable data; they do
not prove an existing human session works against the live service.

Restore checks use `scripts/restore_common.py` for the private workspace, lock, subprocess limits, report, and guarded cleanup. Application data checks remain in this folder. The [monthly restore schedule](../../playbooks/operations/recovery/README.md) runs the same maintained command and validates its report.
