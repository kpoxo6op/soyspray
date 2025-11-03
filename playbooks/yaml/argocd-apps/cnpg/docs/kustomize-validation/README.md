# Kustomize Validation

Quick commands to preview and validate manifests before ArgoCD applies them.

## Preview What ArgoCD Will Apply

```bash
# From cnpg directory
kubectl kustomize immich-db/overlays/initdb
kubectl kustomize immich-db/overlays/prod
kubectl kustomize immich-db/overlays/restore
```

## Test With Suffix (Simulate ArgoCD)

```bash
# Test with -a suffix
cd immich-db/overlays/initdb
kustomize edit set namesuffix -- -a
kubectl kustomize .
git restore kustomization.yaml

# Or use temporary wrapper
cd /tmp
mkdir test && cd test
cat > kustomization.yaml << EOF
nameSuffix: -a
resources:
  - ../../path/to/soyspray/playbooks/yaml/argocd-apps/cnpg/immich-db/overlays/initdb
EOF
kubectl kustomize .
```

## Validate Specific Resources

```bash
# Check Secret name gets rewritten
kubectl kustomize immich-db/overlays/initdb | grep -A3 "secret:"

# Check Cluster name has suffix
kubectl kustomize immich-db/overlays/initdb | grep "name: immich-db"

# Check ScheduledBackup references correct cluster
kubectl kustomize immich-db/overlays/prod | grep -A5 "kind: ScheduledBackup"

# Verify extensions loaded
kubectl kustomize immich-db/overlays/initdb | grep -A10 "postInitSQL"
```

## Common Checks

```bash
# Ensure all overlays build without errors
for overlay in initdb prod restore; do
  kubectl kustomize immich-db/overlays/$overlay >/dev/null && echo "✓ $overlay"
done

# Count resources per overlay
kubectl kustomize immich-db/overlays/initdb | grep "^kind:" | sort | uniq -c
kubectl kustomize immich-db/overlays/prod | grep "^kind:" | sort | uniq -c
kubectl kustomize immich-db/overlays/restore | grep "^kind:" | sort | uniq -c
```
