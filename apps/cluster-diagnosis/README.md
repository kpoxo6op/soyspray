# Laptop cluster diagnosis

This adapter polls Alertmanager through the laptop OpenClaw command scheduler.
Only changed, active, unsuppressed critical incidents can start a diagnosis.
Ordinary timestamp refreshes do not start another model call.

## State and limits

A file lock serializes runs. A private, atomically replaced JSON file stores
incident hashes, attempts, pending delivery, and source status. Interrupted
attempts are not repeated for the same incident. Failed Telegram delivery is
retried without another model call. Delivery can repeat if the process stops
after Telegram accepts a message but before the state file is saved.

The adapter permits three attempts per Auckland calendar day. It checks both
Codex allowance windows before each attempt. Unknown usage prevents a model
call. At 55% usage, new diagnosis stops; at 60%, it reports the usage limit.
These unattended limits are independent of a human-approved interactive run.
Active model runs check usage every 30 seconds and stop at 65% or when usage
cannot be read. The adapter never consumes a reset or buys credits.

## Execution boundary

Bubblewrap hides the laptop home, host processes, private temporary files,
and deployment credentials. The native Codex executable and its installed code execution helper run in their
own PID namespace. Its temporary home contains only the selected profile's auth file.
The npm JavaScript launcher is resolved to its installed native executable.
Codex uses its workspace-write sandbox, without automatic approval or user
configuration. Each model process has a 20-minute timeout. The outer process
group and PID namespace provide child cleanup.

No Kubernetes credential is mounted. A supplied kubeconfig is rejected because
read-only Pod and Deployment access can disclose inline passwords. The model
receives selected resource labels and numeric Prometheus readings. Fixed queries
run outside the model sandbox through the existing node-0 SSH route. Neither
alert text nor model commands enter that SSH command. Free-text annotations,
workload bodies, logs, URLs, and arbitrary labels are excluded from its prompt.
The model must state these evidence limits. Prompt instructions are not the
credential boundary.

Use a dedicated, credential-free draft directory. Do not use the operational
checkout or a Git worktree with a link to the main repository's Git directory.
Each attempt gets a new private draft directory. A committed source archive is
mounted read-only at `/source`, without a shared Git directory. Only the draft
directory is writable. The adapter cannot merge or deploy a fix.
A human must review any suggested patch and test it through normal repository
commands.

## Setup and checks

Use the shared installed-runtime operation from a committed, pushed revision:

```sh
source soyspray-venv/bin/activate
ansible-playbook playbooks/operations/runtime/install.yml \
  -e operations_revision=COMMIT -e diagnosis_telegram_target=RECIPIENT \
  -e diagnosis_enabled=true
```

The installer creates a disabled native job, seeds a separate account profile
without overwriting refreshed credentials, and archives committed source. It
also installs the metrics endpoint for Grafana's Soyspray Operations view.
The existing evidence collector timer is unchanged. The root-owned
`soyspray-evidence-route.service` keeps only TCP port 9910 replies to the LAN on
the local route. It does not change shared Tailscale settings. The endpoint
binds to `192.168.20.50`; update its bind, reply rule, and Prometheus target
together if this address changes. The job and endpoint use the pinned
`~/.local/lib/soyspray-operations/current` checkout.

Before enabling, verify the selected account, native model execution, tool
network denial, timeout cleanup, Telegram delivery, and the live metrics.
Repeat the installer with `-e diagnosis_enabled=true` after acceptance. Stop the
job with `-e diagnosis_enabled=false`. To change its subscription, disable the
job and sign in with `CODEX_HOME=~/.local/state/soyspray/cluster-diagnosis/profile
codex login`; verify usage before enabling it again.

Run the focused checks:

```sh
python3 apps/cluster-diagnosis/tests/test_adapter.py
```

The tests include the actual installed Codex argument parser and Bubblewrap
mounts, hidden host credentials and processes, source failures, delivery retry,
restart, duplicate incidents, and allowance limits. Native launcher tests skip
when their executables are absent; a skip is not live acceptance.

Prepare a disabled native command job with the installed OpenClaw CLI:

```sh
openclaw cron add --name cluster-diagnosis --cron '*/2 * * * *' --disabled \
  --tz Pacific/Auckland --exact --no-deliver \
  --timeout-seconds 1260 --no-output-timeout-seconds 1260 \
  --command-argv '["python3","/path/to/checkout/apps/cluster-diagnosis/app/adapter.py"]' \
  --command-cwd /path/to/checkout \
  --command-env ALERTMANAGER_URL=http://192.168.20.35:9093 \
  --command-env TELEGRAM_TARGET='<approved-telegram-target>' \
  --command-env CLUSTER_DIAGNOSIS_WORKSPACE=/path/to/private-draft \
  --command-env CODEX_BIN=/home/boris/.local/bin/codex \
  --command-env CLUSTER_DIAGNOSIS_CODEX_HOME=/path/to/diagnosis-profile
```

Keep direct Alertmanager alerts and external checks active. Disable this named
job through `openclaw cron disable JOB_ID` to stop diagnosis. Retain its state to
avoid repeating incidents after restart. Keep the separate release-review job
paused until its agreed observation period and review boundary.
