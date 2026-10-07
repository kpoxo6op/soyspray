# Node-0 OpenClaw retirement

## Legacy DeepSeek Harness route name

`opencode-remote.yml` removes the old `opencode-remote` Argo Application,
namespace, route, and AppProject after the replacement `ai` Application is
Synced. It then waits for the renamed relay and verifies its Service, Ingress,
and Certificate exist.

Run it only after `ai` is present in Argo CD:

```bash
source soyspray-venv/bin/activate
python -m pip install -r playbooks/operations/retirement/requirements.in
ansible-playbook playbooks/operations/retirement/opencode-remote.yml \
  -e confirm_ai_rename=true
```

The operation is safe to rerun. It does not change the laptop, shared ingress,
DNS provider credentials, or any namespace other than `opencode-remote`.

## Node-0 OpenClaw

OpenClaw runs on the laptop. `node0-openclaw.yml` removes only the verified
old installation on node-0. Keep this operation through the migration window.

Push the branch and run `make go`. Then check the exact node-0 operation:

```bash
source soyspray-venv/bin/activate
ansible-playbook -i inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  playbooks/operations/retirement/node0-openclaw.yml --check
```

Omit `--check` to apply. The playbook checks the host name, dedicated account,
service owner, cron scope, module package names, binary targets, and old state
folders first. It stops if those facts differ from the inspected installation.

It removes the dedicated cron and native jobs, stops and disables gateway
services, removes the whole system unit and drop-in directory, disables linger,
and removes the account, home, copied kubeconfig, credentials, browser state,
and verified OpenClaw modules. It stops the dedicated user manager without
killing processes by UID across Kubernetes containers.

The final audit requires no OpenClaw processes, services, schedules, or
listeners. It compares the protected tool files and the Tailscale service and
process before and after. Node.js, npm, Kubernetes tools, Chrome, Playwright,
and `/etc/kubernetes/admin.conf` stay in place. Credentials are not revoked or
rotated. The laptop installation is outside the target inventory.

After verified absence, delete the obsolete node-0 installation and maintenance
files. Keep the retirement playbook through the migration window. A completed
retirement can be checked and applied again. Reinstallation needs a separate
reviewed operation; this playbook does not recreate the host installation.

## Cluster diagnosis

`cluster-diagnosis.yml -e retire_cluster_diagnosis=true` retires the supplemental
writer after its Argo child is removed through Git. Run with `--check` first,
then apply delivered `main`. It checks exact ownership and UID preconditions,
stops the writer, and deletes its objects and dedicated state claim. The claim's
verified Delete policy lets Longhorn reclaim only its bound PV and volume;
the operation waits for both to disappear. The unused dedicated provider Secret
is also retired if present. Shared monitoring and Telegram identity are retained.

Verify unchanged Alertmanager configuration, zero delivery failures, firing
Watchdog, and healthy remaining Applications without sending a synthetic alert.
Rollback through a CI-green Git revert to restore the pinned writer and objects.
The retired incident ledger is not recoverable from Git; a recreated claim starts
empty. Preserve shared delivery credentials and all unrelated application data.

The earlier `laptop-cluster-diagnosis.yml` operation preserves its private local
ledger and does not reinstall the loop. Laptop evidence units are retired;
keep the independent recovery-input-backup timer enabled.

## Retired laptop scrape

After the laptop scrape is removed from the Prometheus package, the stack's
non-pruning owner retains its old generated configuration Secret.
`laptop-scrape.yml -e retire_laptop_scrape=true` removes only that unused Secret
from delivered `main`. Run with `--check` first. It requires the original single
laptop job, exact stack ownership, no Prometheus reference, and UID deletion
preconditions. It never touches Alertmanager or its shared delivery identity.
