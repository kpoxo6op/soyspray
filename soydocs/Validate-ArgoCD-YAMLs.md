# Validate ArgoCD YAMLs

<https://go.dev/doc/install>

```sh
wget https://go.dev/dl/go1.23.2.linux-amd64.tar.gz
sudo tar -C /usr/local -xzf go1.23.2.linux-amd64.tar.gz
export PATH=$PATH:/usr/local/go/bin
go version
#go version go1.23.2 linux/amd64
```

<https://github.com/yannh/kubeconform?tab=readme-ov-file#installation>

```sh
go install github.com/yannh/kubeconform/cmd/kubeconform@v0.6.7
export PATH=$PATH:$(go env GOPATH)/bin
source ~/.bashrc
kubeconform -h
```

```sh
kubeconform -summary -schema-location default -schema-location 'https://raw.githubusercontent.com/datreeio/CRDs-catalog/refs/heads/main/argoproj.io/application_v1alpha1.json' playbooks/argocd/apps/prometheus/prometheus-application.yaml
```
