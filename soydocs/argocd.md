# ArgoCD

## Expose ArgoCD

To expose ArgoCD, the service was configured as a LoadBalancer in Kubernetes and
assigned the IP 192.168.1.21 using MetalLB.

The `argocd-cmd-params-cm` config map was updated to ensure that ArgoCD would
operate in insecure mode by keeping the `server.insecure` key set to "true". This
change enabled HTTP access without requiring HTTPS.

After updating the configuration, the argocd-server deployment was restarted to
apply the changes. The new pod was successfully started, exposing ArgoCD via
HTTP.

ArgoCD was then available at `http://192.168.1.21`.

## Configure ArgoCD

```sh
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu main.yml --tags argocd
```

This command configures ArgoCD with necessary settings:

1. It applies the `argocd-cm` ConfigMap with `application.instanceLabelKey: argocd.argoproj.io/instance`
2. This prevents ArgoCD from overwriting the important `app.kubernetes.io/instance` labels
3. Without this setting, ServiceMonitors in applications like Prometheus may fail to find their targets
4. The ArgoCD server deployment is restarted to apply the changes

## How to Apply Argo CD Applications

```sh
cd soyspray

ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu playbooks/argocd/playbooks/deploy-apps.yml
```

## ArgoCD CLI Management

Use the `argocd` CLI for command-line management of the Longhorn application.

### Login

```bash
argocd login argocd.soyspray.vip
kubectl config set-context --current --namespace=argocd
```

### Common Commands

```bash
argocd app list
argocd app get longhorn
argocd app sync longhorn --dry-run
argocd app sync longhorn
argocd app manifests longhorn
argocd app sync longhorn --preview-changes
```
