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
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
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

## Laptop incident diagnosis

`laptop-cluster-diagnosis.yml` removes the OpenClaw cron job that ran the
diagnosis adapter on the laptop. The loop now runs in the cluster as
`monitoring/cluster-diagnosis` and needs no laptop process.

```bash
source soyspray-venv/bin/activate
ansible-playbook playbooks/operations/retirement/laptop-cluster-diagnosis.yml --check
ansible-playbook playbooks/operations/retirement/laptop-cluster-diagnosis.yml
```

It copies the retired ledger to `state.retired.json` and leaves both files in
place. The cluster keeps its own ledger on
`monitoring/cluster-diagnosis-state`. Delete the laptop copy only after the
Application has been Synced and Healthy for a day. It is safe to rerun, and it
reports honestly when OpenClaw is not installed.

Do not remove `soyspray-evidence-metrics.service` or its timers: they keep
serving backup and restore evidence.
