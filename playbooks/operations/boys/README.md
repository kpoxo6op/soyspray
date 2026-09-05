# Boys runtime input

Bootstrap the initial trip from an encrypted file on the operator machine.
This operation creates only `boys/boys-trip-seed`. It requires the existing
bound `boys-data` claim and does not change the PIN or session key.

Create a file outside the repository with `ansible-vault create`. Use
`boys_trip_seed` as its top-level key, with an `id` and `document` accepted by
the [Boys data interface](../../../kubernetes/boys/README.md). Keep destination,
dates, and private content in this encrypted file. Keep its Vault password and
an offline copy outside the cluster. Do not put either in Git or shell history.

Push the operation branch, run `make go`, then use the normal inventory:

```sh
source soyspray-venv/bin/activate
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  playbooks/operations/boys/bootstrap-trip.yml \
  --vault-password-file "$HOME/.config/soyspray/recovery/vault-password" \
  -e boys_trip_vault_file="$HOME/.config/soyspray/recovery/boys-trip.vault.yml"
```

Use `--check` first. The schema check runs locally without writing data.
Sensitive tasks suppress their output. A repeat with the same input makes no
change. A different existing seed stops the operation. The Secret is immutable
and protected from Argo pruning and deletion.

Bootstrap before promoting the image configuration that mounts `seed.json`
and sets `BOYS_TRIP_SEED_FILE`. Source-only merges do not activate that input.
The application seeds one draft once and never replaces later edits. Change
an active trip through the authenticated interface. Keep the seed archive for
a full recovery; it is not the current trip backup. Longhorn protects current
trip documents and audit history with the rest of the Boys database.
