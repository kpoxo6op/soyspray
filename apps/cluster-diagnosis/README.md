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
The adapter never consumes a reset or buys credits.

## Execution boundary

Bubblewrap hides the laptop home, host processes, private temporary files,
and deployment credentials. The native Codex executable runs in its own PID
namespace. Its temporary home contains only the selected profile's auth file.
The npm JavaScript launcher is resolved to its installed native executable.
Codex uses its workspace-write sandbox, without automatic approval or user
configuration. Each model process has a 20-minute timeout. The outer process
group and PID namespace provide child cleanup.

No Kubernetes credential is mounted. A supplied kubeconfig is rejected because
read-only Pod and Deployment access can disclose inline passwords. The model
receives only selected resource labels from the incident. Free-text annotations,
workload bodies, logs, URLs, and arbitrary labels are excluded from its prompt.
The model must state these evidence limits. Prompt instructions are not the
credential boundary.

Use a dedicated, credential-free draft directory. Do not use the operational
checkout or a Git worktree with a link to the main repository's Git directory.
Only the draft directory is writable. The adapter cannot merge or deploy a fix.
A human must review any suggested patch and test it through normal repository
commands.

## Setup and checks

The adapter is not enabled by this source change. Before enabling a command job,
verify the chosen account, native model execution, denial of tool network access,
timeout cleanup, Telegram delivery, and the evidence needed for useful diagnosis.
The Grafana operations view and full task acceptance remain separate work.

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
