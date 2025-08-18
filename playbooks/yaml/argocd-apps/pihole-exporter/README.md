# Pihole Exporter

Prometheus exporter for Pihole

<http://192.168.1.122/admin/settings.php?tab=api>

`Raw API Token: 9xxxxxxxxxxxxxREDACTEDxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxbb`

Trying using current Pihole password for now.

## Check the Exporter

left ear

`kubectl port-forward svc/pihole-exporter -n pihole 9617:9617`

right ear

`curl http://localhost:9617/metrics`

Manual patch to remove finalizers when ArgoCD delete is stuck

```sh
kubectl patch application pihole-exporter -n argocd --type=json --patch='[{"op": "remove", "path": "/metadata/finalizers"}]'
```
