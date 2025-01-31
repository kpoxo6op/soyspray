# ArgoCD

## Expose ArgoCD

To expose ArgoCD, the service was configured as a LoadBalancer in Kubernetes and
assigned the IP 192.168.1.121 using MetalLB.

The `argocd-cmd-params-cm` config map was updated to ensure that ArgoCD would
operate in insecure mode by keeping the `server.insecure` key set to "true". This
change enabled HTTP access without requiring HTTPS.

After updating the configuration, the argocd-server deployment was restarted to
apply the changes. The new pod was successfully started, exposing ArgoCD via
HTTP.

ArgoCD was then available at `http://192.168.1.121`.

```sh
cd soyspray
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu main.yml --tags expose-argocd
```

## Enable Kustomize

```sh
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu main.yml --tags enable-kustomize-argocd
```

## How to Apply Argo CD Applications

```sh
cd soyspray

ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu playbooks/install-k8s-python-libs.yml

ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu playbooks/manage-argocd-apps.yml
```
