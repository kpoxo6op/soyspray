# Node-0 OpenClaw retirement

OpenClaw runs on the laptop. The old node-0 removal entry point now imports
`../retirement/node0-openclaw.yml`. It no longer removes shared dependencies.
Do not use the old installation or maintenance playbooks during retirement.

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
