# jenkins

Basic Jenkins app for ArgoCD-driven test deployments.

## What it provisions

- Installs Jenkins from the Jenkins community Helm chart.
- Configures a known admin account (`jenkins-admin` / `jenkins-admin-pass`).
- Runs an init Groovy bootstrap that:
  - creates a user (`cloudbees-cli`) if missing,
  - generates an API token for that user,
  - creates a basic freestyle job named `silly-job` that runs `echo "silly job executed from bootstrap"`.

## Deploy with ArgoCD

```sh
source soyspray-venv/bin/activate && ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu playbooks/deploy-argocd-apps.yml
```

## Notes

- Bootstrap output (including the generated API token) is printed to the Jenkins controller logs at startup.
