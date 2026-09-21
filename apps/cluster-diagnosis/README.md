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
  inside a 15-minute window. The bounds are aggregate for the whole incident,
  not per target: 6 targets, 40 lines per target, 120 lines and 512 KiB in
  total. A response larger than 1 MiB is rejected before it is parsed.
- Every line is normalized, then parsed. Only allowlisted fields leave the
  module: a level from a fixed vocabulary, a source from a charset-restricted
  allowlist, and a message from a fixed key list. Field values are rejected if
  they contain control characters, URLs with credentials, secret shapes
  (including `password is ...`, AWS key ids and JWTs), bearer tokens,
  private-key blocks, e-mail addresses, card-length digit runs or long
  high-entropy tokens.
- A message is exported only when the fixed signal vocabulary recognizes it.
  Everything else - free text, personal records, application payloads and
  injected instructions - stays local. No secret pattern can enumerate those,
  so the rule is an allowlist by construction rather than a scrubber.
- Held-back content is never silent: each case becomes an explicit
  `message-held-back` or `text-format-not-exported` gap. A selector that cannot
  be built from safe label values produces an `unsafe-selector` or
  `no-log-selector` gap, and a budget that stops a read produces an
  `incident-budget-reached` gap.
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
- Bounds: 64 inputs per batch, two batches per invocation, 400 characters per
  line, 32 KiB per payload, 8-second socket timeout, up to two retries per
  batch, 25-second wall-clock budget, 256 KiB response cap, 1500 classifications
  per day, 2000 cache entries.
- The daily allowance is reserved before a batch is dispatched and a batch is
  trimmed to what remains, so a request that completes remotely but times out
  locally is still counted. A spent budget stops the next batch instead of
  starting it.
- Low confidence, `unscored` input, a label outside the requested set, a
  malformed body, a 4xx, a persistent 429, a 5xx or a network fault all produce
  `unknown or insufficient evidence` with an explicit cause. Nothing raises.
- A serving model that does not start with `jev-` is reported as an unexpected
  substitution in the narrative and in the metrics.
- The classifier is a relevance and routing hint. It is never proof of health
  or of a root cause, and it has no authority to suppress an alarm or authorize
  a change. A `normal or recovered` hint does not stop a critical incident from
  being diagnosed, and the prompt says so. Substitution is checked on the batch
  model, on every entry of `modelsUsed`, and on each result's own model.

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

Prove the integrated path without touching the cluster: point one adapter run at
a local Alertmanager fixture, with its own private state, and use the real
collector, classifier, sandbox and approved Telegram target.

```sh
export ACCEPT="$(mktemp -d)"
install -d -m 700 "$ACCEPT/state"
TARGET="$(openclaw cron list --all --json | python3 -c \
  'import json,sys; print([j["payload"]["env"]["TELEGRAM_TARGET"] for j in json.load(sys.stdin)["jobs"] if j["name"]=="cluster-diagnosis"][0])')"

# Fixture: one critical incident for a namespace that really exists.
cat > "$ACCEPT/fixture.py" <<'PY'
import json, sys, http.server
resolved = len(sys.argv) > 1 and sys.argv[1] == "resolved"
alerts = [{
    "fingerprint": "acceptance-1",
    "labels": {"alertname": "SoysprayPodCrashLooping", "severity": "critical",
               "namespace": "immich", "pod": "immich-server-0", "container": "server"},
    "annotations": {"summary": "controlled acceptance fixture"},
    "status": {"state": "active", "silencedBy": [], "inhibitedBy": []},
    "startsAt": "2026-01-01T00:00:00Z",
    "endsAt": "2026-01-01T00:10:00Z" if resolved else "2099-01-01T00:00:00Z",
}]
class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps(alerts).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *args):
        return
http.server.ThreadingHTTPServer(("127.0.0.1", 9099), Handler).serve_forever()
PY

run() {
  ALERTMANAGER_URL=http://127.0.0.1:9099 TELEGRAM_TARGET="$TARGET" \
  python3 apps/cluster-diagnosis/app/adapter.py \
    --state "$ACCEPT/state/state.json" --lock "$ACCEPT/state/lock" \
    --workspace "$ACCEPT/state/drafts" \
    --evidence-root "$ACCEPT/state/evidence" \
    --metrics-path "$ACCEPT/state/metrics.json"
}

python3 "$ACCEPT/fixture.py" & sleep 1
echo "first run: $(run)"      # expect: diagnosed
kill %1

cat > "$ACCEPT/check.py" <<'PY'
import json, sys
from pathlib import Path
state = json.loads((Path(sys.argv[1]) / "state/state.json").read_text())
metrics = json.loads((Path(sys.argv[1]) / "state/metrics.json").read_text())
assert state["attempts"], "no attempt was charged"
assert metrics["collector"]["status"] != "unknown", "the collector never ran"
assert metrics["classifier"]["status"] != "unknown", "the classifier never ran"
assert metrics["metrics"]["last_outcome"] == "diagnosed", metrics["metrics"]
assert not [record for record in state["incidents"].values() if record.get("delivery_pending")]
assert not list((Path(sys.argv[1]) / "state/drafts").glob("incident-*/.diagnosis-output"))
print("collector:", metrics["collector"]["status"],
      "| classifier:", metrics["classifier"]["status"],
      "| model:", metrics["classifier"]["model"])
PY
python3 "$ACCEPT/check.py" "$ACCEPT"

# Recovery: the same incident, now resolved. No second model call.
python3 "$ACCEPT/fixture.py" resolved & sleep 1
echo "second run: $(run)"     # expect: recovered
kill %1
rm -rf "$ACCEPT"
```

The first run must print `diagnosed`, the second `recovered`, and the check must
pass. The first run spends one real model attempt, so run it only when that is
acceptable. Delete the fixture state afterwards so live incidents start clean.

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

## Deployment order

Argo CD syncs the `loki` and `kube-prometheus-stack` Applications from the same
revision but not atomically. A short window is expected:

- Editing an Alloy ConfigMap does not reload Alloy. Bump
  `soyspray.dev/signal-config` on both Alloy workloads whenever the pipeline
  changes so the pod template changes and the pods roll.
- The new Prometheus rules begin as soon as the operator reloads them, and they
  evaluate the derived counters, so a failure that happens during the window is
  still inside the rule window after the reload.
- Loki keeps the raw evidence throughout. Only its own rule evaluation stops.

After the merge, confirm the rules are loaded, the counters are scraped and the
Loki ruler is gone before calling the cutover complete.

## Rollback

1. `openclaw cron disable JOB_ID` stops new diagnosis. Native alerting,
   Alertmanager delivery and the external watchdog are unaffected.
2. Reinstall the previous release. The installer resolves `operations_revision`
   through `git rev-parse` in the reviewed checkout, so it wants the commit, not
   the release directory:

   ```sh
   ansible-playbook playbooks/operations/runtime/install.yml \
     -e operations_revision="$(basename "$(readlink -f ~/.local/lib/soyspray-operations/previous)")"
   ```
3. Convert the incident state before starting the previous adapter, which
   understands only version 1 and stops on a version 2 file:

   ```sh
   python3 - <<'PY'
   import json, os
   from pathlib import Path
   path = Path.home() / ".local/state/soyspray/cluster-diagnosis/state.json"
   state = json.loads(path.read_text())
   Path(str(path) + ".v2").write_text(json.dumps(state, indent=1))
   path.write_text(json.dumps({"version": 1, "source": state.get("source"),
                               "alerts": {}, "attempts": state.get("attempts", {})}))
   os.chmod(path, 0o600)
   PY
   ```

   The daily attempt counts carry over, so the day cannot overspend during the
   rollback.
4. To restore the retired Loki ruler rules, revert the Loki and Prometheus
   commits together. Bump `soyspray.dev/signal-config` on both Alloy workloads
   in the same revert so the old pipeline rolls out. The Loki Application prunes
   nothing back automatically: the reverted manifests recreate the rule
   ConfigMaps, and Loki loads them on its next rollout.
5. Disabling the job stops new runs. An attempt already inside the model keeps
   running until it finishes or hits its 20-minute timeout, and the file lock
   prevents a second run from starting meanwhile.
