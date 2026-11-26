# Irrigation guide

The read-only static field guide is served at https://explain.soyspray.vip/irrigation/ over the LAN and tailnet. The existing explain ingress supplies the host certificate. The guide has no credentials, watering controls, uploads or cluster API access. A dedicated prebound local PV on node-0 exposes a single edition read-only to unprivileged nginx.

The media and rendered pages live in the private controller-side project. Generate its SHA256SUMS for every content file. Stage the named edition using the pushed playbook before promoting its subPath in the Deployment.

```sh
ansible-playbook -i inventory/soycluster/hosts.yml playbooks/operations/irrigation-guide/publish.yml -u ubuntu -e guide_source=/absolute/private/export -e guide_edition=release-01
kubectl kustomize apps/irrigation-guide/manifests >/dev/null
```

Verify the Argo application, the HTTPS page and a range request for the film. Recovery consists of republishing the same verified private edition on a replacement node-0. Roll back a content change by restoring the preceding edition's subPath. PV and claim are retained on application deletion. This volume holds only reproducible publications and does not replace the controller's originals.
