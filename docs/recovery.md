# Recovery

Recovery statements must name the evidence behind them. These states are not
interchangeable:

| Evidence | What it proves |
| --- | --- |
| Backup configured | A policy or schedule exists. It does not prove that a backup completed. |
| Backup completed | Native backup state contains a recovery point. It does not prove the application can use it. |
| Isolated restore passed | A selected backup restored into a separate workspace and passed its maintained data checks. |
| Human journey passed | A person or maintained browser journey used the restored application as intended. |

## Read recovery evidence

```sh
kubectl get backups.postgresql.cnpg.io -A
make restore-check APP=boys
```

Restore checks must use isolated claims and guarded cleanup. They must preserve
the production identity and data. A missing or stale report is unknown, not a
successful recovery.

Destructive recovery work requires exact scope, current backup evidence, and
the confirmation required by the maintained procedure.

See the [recovery operations](https://github.com/kpoxo6op/soyspray/tree/main/playbooks/operations/recovery)
for the authoritative commands and limits.

For node maintenance, follow the [native Kubespray procedure](https://github.com/kpoxo6op/soyspray/tree/main/playbooks/operations/nodes).
The completed drills do not require repeating. Preserve filesystem, storage,
and device identities; do not add a recurring manual drill.

The daily [recovery-input backup](https://github.com/kpoxo6op/soyspray/tree/main/apps/recovery-input-backup)
remains enabled for all private recovery inputs, node configuration and unique voice models. It
verifies restored off-laptop content automatically. The production monitoring
path uses native backup records and alerts; no laptop evidence job is required.


The recovery-input README names the include set and root of trust. One human
step remains: store the recovery Vault password, Restic password, restricted S3
AWS key pair and repository address in an independently accessible password
manager. No independent unlock copy was established by the automated restore.


The 2026-10-07 recovery-input service run verified 43 restored files and all 29
local originals by checksum, with completed cleanup and an enabled/active timer.
This is an actual off-laptop input restore, not a whole-cluster restore proof.
