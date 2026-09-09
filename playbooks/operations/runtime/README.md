# Installed laptop operations

One Ansible operation installs evidence collection, monthly isolated restores,
recovery-input backups, diagnosis, and metrics under
`~/.local/lib/soyspray-operations`. Each immutable release has its own Git
checkout and Python environment. `current` selects the active release and
`previous` retains the prior one for rollback. Private credentials, reports,
locks, incident state, and model inputs remain outside the checkout.

The installed environment uses `requirements-recovery.txt`. It contains the
Ansible and YAML dependencies used by recovery operations. It does not install
npm packages, a browser, pytest, ruff, or ansible-lint. Those remain delivery
dependencies in `requirements-dev.txt` and the normal `make go` gate.

Install or update an exact pushed commit:

```sh
source soyspray-venv/bin/activate
ansible-playbook playbooks/operations/runtime/install.yml \
  -e operations_revision=COMMIT \
  -e diagnosis_telegram_target=RECIPIENT \
  -e diagnosis_enabled=true
```

Run the same command with `--check` before an update. To roll back, use the
commit shown by `readlink ~/.local/lib/soyspray-operations/previous` as
`operations_revision`. The installer keeps systemd unit names and OpenClaw job
identity unchanged.

Before selecting a release, the installer proves that the exact commit exists
on GitHub, rejects tracked changes in the installed checkout, and syntax-checks
the emergency restore playbooks. These checks do not replace `make go` or the
GitHub checks required before delivery.

Check the installation with `systemctl --user status` for
`soyspray-operations-evidence.timer`, `soyspray-restore-check.timer`,
`soyspray-recovery-input-backup.timer`, and `soyspray-evidence-metrics.service`.
Use `openclaw cron list --all --json` for diagnosis. Run a recovery-input backup
through its installed service. Run a critical isolated restore with the pinned
Python command under `current`; reports remain in `~/.local/state/soyspray`.

The runtime does not update itself. It keeps all releases until an operator
removes an unreferenced old release after verification.
