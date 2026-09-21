# Laptop cluster diagnosis

This adapter turns one operational incident into one investigation and one
Telegram explanation. It polls Alertmanager through the laptop OpenClaw command
scheduler, folds related alerts into incidents, collects bounded read-only
evidence, asks the Jev classifier for a semantic hint, and runs one isolated
reasoning worker for a changed incident.

## Incident identity and lifecycle

An incident is one thing a human would investigate.

- A namespaced alert belongs to its application, so `KubePodCrashLooping`,
  `SoysprayVolumeMountFailure` and a failed backup job in `immich` are three
  symptoms of one incident.
- A node alert without a namespace belongs to the node.
- A node incident also owns application incidents that started around it and
  whose firing pods all sit on that node. Those consequences are named in the
  node narrative and do not each spend an attempt. They become independent
  again when the node incident closes. An unreadable node-to-pod mapping never
  merges anything.
- Anything else falls back to its named resource, then to its alert name.

The lifecycle is `open` -> material change -> `closed`, with bounded reopen.
Refresh timestamps, silences and inhibition do not create an incident. A symptom
that resolves, is inhibited, or stops being reported closes after a three-minute
grace, and the adapter sends one recovery message. A reopened anchor inside six
hours continues the generation chain and is reported as reopened.

Only `critical` incidents spend a model attempt, plus a warning-level root
incident that owns critical consequences. Attempts are charged to the incident,
not to each symptom. Limits: three attempts per incident generation, three
attempts per Auckland calendar day, and one model call per scheduler
invocation. Independent incidents wait their turn; the longest-waiting incident
goes first.

## Evidence boundary

The collector runs in the adapter process, outside the model sandbox.

- It reads only the Loki log lines for the incident's own resource selection,
  inside a 15-minute window, bounded to 6 targets, 40 lines per target,
  120 lines and 512 KiB per incident.
- Every line is normalized, then parsed. Only allowlisted fields leave the
  module: a level from a fixed vocabulary, a source from a charset-restricted
  allowlist, a bounded message from a fixed key list, and signal names from a
  fixed list. Field values are rejected if they contain control characters,
  URLs with credentials, key/value secret shapes, bearer tokens, private-key
  blocks, e-mail addresses, card-length digit runs or long high-entropy tokens.
- A free-text line is never exported. It contributes its signal names and an
  explicit `text-format-not-exported` gap. A selector that cannot be built from
  safe label values produces an `unsafe-selector` or `no-log-selector` gap.
- Raw log lines are never stored on the laptop. The sanitized pack is kept
  privately under `~/.local/state/soyspray/cluster-diagnosis/evidence` with mode
  `0600` and a 20-pack retention.
- Alert annotations, workload bodies, environment values and Kubernetes
  credentials never enter the prompt. The model sees only allowlisted labels,
  fixed Prometheus queries, the sanitized pack and the classifier summary.
- All of that is presented inside a block that the prompt marks as untrusted
  data, including prompt injection. The sandbox has no cluster credentials, no
  network and no ability to merge or deploy, so injected text cannot act.

SSH to node-0 carries a fixed local script and a base64-encoded request built
only from charset-validated label values. No alert text, log line or model
command enters that SSH command.

## Jev classification

The adapter posts sanitized evidence lines to `https://classifier.dev` (the
Jev fast route) with six semantic labels: `storage failure`,
`network or DNS failure`, `authentication or permission failure`,
`application crash or resource exhaustion`, `normal or recovered`, and
`unknown or insufficient evidence`.

- Identical normalized lines are sent once, cached by hash, and reused.
- Bounds: 64 inputs per request, two requests per invocation, 400 characters per
  line, 32 KiB per payload, 8-second request timeout, two retries with backoff,
  25-second total budget, 1500 classifications per day, 2000 cache entries.
- Low confidence, `unscored` input, a label outside the requested set, a
  malformed body, a 4xx, a persistent 429, a 5xx or a network fault all produce
  `unknown or insufficient evidence` with an explicit cause. Nothing raises.
- A serving model that does not start with `jev-` is reported as an unexpected
  substitution in the narrative and in the metrics.
- The classifier is a relevance and routing hint. It is never proof of health
  or of a root cause, and it has no authority to suppress an alarm or authorize
  a change. A `normal or recovered` hint does not stop a critical incident from
  being diagnosed, and the prompt says so.

## Execution boundary

Bubblewrap hides the laptop home, host processes, private temporary files, and
deployment credentials. The native Codex executable and its installed code
execution helper run in their own PID namespace. Its temporary home contains
only the selected profile's auth file. Codex uses its workspace-write sandbox,
without automatic approval or user configuration. Each model process has a
20-minute timeout. The outer process group and PID namespace provide child
cleanup.

No Kubernetes credential is mounted. A supplied kubeconfig is rejected because
read-only Pod and Deployment access can disclose inline passwords.

Use a dedicated, credential-free draft directory. Do not use the operational
checkout or a Git worktree with a link to the main repository's Git directory.
Each attempt gets a new private draft directory. A committed source archive is
mounted read-only at `/source`, without a shared Git directory. Only the draft
directory is writable. The adapter cannot merge or deploy a fix. A human must
review any suggested patch and test it through normal repository commands.

## Spending limits

The adapter permits three attempts per Auckland calendar day and three per
incident generation. It checks both Codex allowance windows before each attempt.
Unknown usage prevents a model call. At 55% usage, new diagnosis stops; at 60%,
it reports the usage limit. These unattended limits are independent of a
human-approved interactive run. Active model runs check usage every 30 seconds
and stop at 65% or when usage cannot be read. The adapter never consumes a reset
or buys credits.

## State, restart and delivery

A file lock serializes runs. A private atomically replaced JSON file stores
incidents, symptoms, attempts, delivery state, classifier cache and counters. A
pre-incident state file keeps only its daily attempt counts, so a cutover cannot
overspend the day.

Interrupted attempts are marked `interrupted` and are not repeated for the same
incident content. Failed Telegram delivery is retried without another model
call, so a stop after Telegram accepts a message can repeat one message but
never repeats the model call. Telegram output is capped at 3500 bytes and
trimmed on a line boundary.

## Metrics and the operations view

Each run writes a private snapshot to
`~/.local/state/soyspray/cluster-diagnosis/metrics.json`. The existing
`soyspray-evidence-metrics` endpoint serves it as `soyspray_incident_*`,
`soyspray_diagnosis_*`, `soyspray_evidence_*` and `soyspray_classifier_*` series.
The **Soyspray Operations** dashboard shows open incidents, diagnosis attempts,
collector state, evidence gaps, classifier state and outcomes. A missing
snapshot produces no series, so the dashboard shows unknown rather than a false
zero.

## Setup and checks

Use the shared installed-runtime operation from a committed, pushed revision:

```sh
source soyspray-venv/bin/activate
ansible-playbook playbooks/operations/runtime/install.yml \
  -e operations_revision=COMMIT
```

The installer preserves an existing declared job's private target and enabled
state. For the first installation only, pass `diagnosis_telegram_target` and
`diagnosis_enabled=true`. It creates a disabled job by default, seeds a separate
account profile without overwriting refreshed credentials, and archives
committed source. It also installs the metrics endpoint for Grafana's Soyspray
Operations view.

The root-owned `soyspray-evidence-route.service` keeps only TCP port 9910
replies to the LAN on the local route. It does not change shared Tailscale
settings. The endpoint binds to `192.168.20.50`; update its bind, reply rule,
and Prometheus target together if this address changes. The job and endpoint use
the pinned `~/.local/lib/soyspray-operations/current` checkout.

Before enabling, verify the selected account, native model execution, tool
network denial, timeout cleanup, Telegram delivery, and the live metrics.
Repeat the installer with `-e diagnosis_enabled=true` after acceptance. Stop the
job with `-e diagnosis_enabled=false`. To change its subscription, disable the
job and sign in with `CODEX_HOME=~/.local/state/soyspray/cluster-diagnosis/profile
codex login`; verify usage before enabling it again.

Run the focused checks:

```sh
python3 apps/cluster-diagnosis/tests/test_adapter.py
python3 apps/cluster-diagnosis/tests/test_incident.py
python3 apps/cluster-diagnosis/tests/test_evidence.py
python3 apps/cluster-diagnosis/tests/test_classify.py
```

The tests cover incident correlation, recovery, reopen, restart, duplicate
delivery, spending limits, collector gaps, sensitive-data exclusion, prompt
injection, classifier failure modes, the installed Codex argument parser, and
the Bubblewrap mounts. Native launcher tests skip when their executables are
absent; a skip is not live acceptance.

### Controlled acceptance run

Prove the integrated path without touching the cluster by pointing one adapter
run at a local Alertmanager fixture instead of the live endpoint. Write a small
HTTP server that returns one alert as a JSON list from `/api/v2/alerts`, for
example a critical `SoysprayPodCrashLooping` for `immich/immich-server-0` with
`container=server`, then run the installed adapter once with
`ALERTMANAGER_URL` pointing at it and the real `TELEGRAM_TARGET`.

The run exercises the real collector, the real classifier, the real sandbox and
the real delivery path without changing the cluster. Set the fixture alert's
`endsAt` in the past to observe the recovery message. Remove the fixture state
file afterwards so live incidents start clean.

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
avoid repeating incidents after restart.

## Rollback

1. `openclaw cron disable JOB_ID` stops new diagnosis. Native alerting,
   Alertmanager delivery and the external watchdog are unaffected.
2. Reinstall the previous release:
   `ansible-playbook playbooks/operations/runtime/install.yml -e
   operations_revision=$(readlink -f ~/.local/lib/soyspray-operations/previous)`.
3. To restore the retired Loki ruler rules, revert the Loki and Prometheus
   commits together. The rules live in Git; the Loki Application prunes the
   removed ConfigMaps and recreates them from the reverted manifests.
4. Incident state is private and additive. Deleting
   `~/.local/state/soyspray/cluster-diagnosis/state.json` makes the next run
   treat active alerts as new incidents.
