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
make backup-status FORMAT=json
make restore-check APP=boys
```

Restore checks must use isolated claims and guarded cleanup. They must preserve
the production identity and data. A missing or stale report is unknown, not a
successful recovery.

Destructive recovery work requires exact scope, current backup evidence, and
the confirmation required by the maintained procedure.

See the [recovery operations](https://github.com/kpoxo6op/soyspray/tree/main/playbooks/operations/recovery)
for the authoritative commands and limits.

For a node rebuild, follow the [node recovery procedure](https://github.com/kpoxo6op/soyspray/tree/main/playbooks/operations/nodes).
If a recovery fix is merged between evacuation and restoration, run current
`main` with the original private evacuation file. Restoration verifies that
the recorded revision belongs to current history and that resource identities
still match.
