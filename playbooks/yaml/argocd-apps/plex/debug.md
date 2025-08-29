# Plex: Deployment Debug & Validation Guide

End-to-end validation guide for stateless Plex server setup with manual library configuration. Includes exact commands, expected outputs, and quick fixes. Designed for ArgoCD-driven deploys with linuxserver/plex:1.41.3 and manual library management.

## What the deployment does

1. **Seeds offline Preferences.xml** into `/config/Library/Application Support/Plex Media Server/`.
2. **Prepares server** for manual library configuration (no automatic library creation).
3. **Mounts `/data`** (read‑only mount of media storage) ready for library setup.
4. **Runs stateless** with `emptyDir` at `/config`, re-seeding on every Pod start.

## One‑time prerequisites

- `kubectl` context points at the cluster that runs ArgoCD.
- The `media` namespace exists or is created by ArgoCD.

## 1) Confirm the Pod is up

```bash
kubectl get pods -n media -l app=plex
```

**Expected output:**
```
NAME                    READY   STATUS    RESTARTS   AGE
plex-7c8b9d4f6d-xyz12   1/1     Running   0          2m
```

**If PENDING:** Check PVC availability:
```bash
kubectl get pvc -n media sonarr-tv
```

**If CrashLoopBackOff:** Check main container logs for postStart errors:
```bash
kubectl logs -n media deployment/plex
```

## 2) Verify postStart library bootstrap

Check the main container logs for postStart execution:

```bash
kubectl logs -n media deployment/plex | grep postStart
```

**Expected output:**
```
[postStart] Starting Plex library setup...
[postStart] Basic Plex server setup complete - ready for manual library creation
```

**If missing postStart logs:** The postStart hook may have failed. Check deployment lifecycle configuration and postStart script execution.

## 3) Verify offline preferences are loaded

```bash
kubectl exec -n media deployment/plex -- cat "/config/Library/Application Support/Plex Media Server/Preferences.xml"
```

**Expected output (key settings):**
```xml
<Preferences
  enableLocalSecurity="0"
  allowedNetworks="192.168.1.0/255.255.255.0"
  PublishServerOnPlexOnlineKey="0"
  MachineIdentifier="..."
  ProcessedMachineIdentifier="..."
  AnonymousMachineIdentifier="..."
  ...
/>
```

**If file missing:** Check that custom-init script ran successfully and volume mounts are correct.

## 4) Check media content is accessible

Verify Plex can see the mounted media storage:

```bash
kubectl exec -n media deployment/plex -- ls -la /data/
```

**Expected output (example):**
```
drwxr-xr-x    3 1000     1000          4096 Dec 15 10:30 .
drwxr-xr-x    1 root     root          4096 Dec 15 10:25 ..
drwxr-xr-x    4 1000     1000          4096 Dec 15 10:30 Twin Peaks (1990)
drwxr-xr-x    3 1000     1000          4096 Dec 15 10:29 Other TV Show
```

**If empty:** Check that the media PVC is properly mounted and contains content.

## 5) Access Plex web interface

Get the service endpoint:

```bash
# If using ingress
kubectl get ingress -n media plex

# If using NodePort/LoadBalancer
kubectl get svc -n media plex
```

Navigate to the Plex URL and verify:

- **No sign-in required** (due to `enableLocalSecurity="0"`)
- **Server is ready** for manual library configuration
- **Media storage is accessible** at `/data` for library creation

## 6) Verify stateless operation

Restart the pod and confirm it rebuilds correctly:

```bash
kubectl rollout restart deployment/plex -n media
kubectl get pods -n media -l app=plex -w
```

Wait for new pod to be `Running`, then repeat steps 2-5. Everything should rebuild identically.

## Common issues & fixes

### Custom-init script fails with "Plex Media Scanner not found"

The linuxserver image may not include the CLI scanner in the expected location.

**Fix:** Update custom-init script to skip library creation and create manually via web UI:

```bash
# Remove/comment out the scanner commands in bootstrap-configmap.yaml:
# "/usr/lib/plexmediaserver/Plex Media Scanner" --add-section...
# "/usr/lib/plexmediaserver/Plex Media Scanner" --scan
```

Then create libraries manually pointing to the appropriate media directories.

### Media content not accessible

Check that media files are properly organized:

```bash
kubectl exec -n media deployment/plex -- find /data -type f | head -10
```

**Expected:** Files should be visible in the mounted media directory.

### Preferences not applied (Plex asks for sign-in)

Verify environment variable is set correctly:

```bash
kubectl exec -n media deployment/plex -- env | grep PLEX_MEDIA
```

**Expected:**
```
PLEX_MEDIA_SERVER_APPLICATION_SUPPORT_DIR=/config/Library/Application Support
```

### PVC mount issues

Check PVC is bound and accessible:

```bash
kubectl describe pvc -n media sonarr-tv
kubectl get pv
```

Ensure the PVC is `Bound` and the underlying storage is healthy.

## Quick validation checklist

- [ ] Pod is `Running` (not `CrashLoopBackOff` or `Pending`)
- [ ] PostStart logs show "Basic Plex server setup complete"
- [ ] Preferences.xml exists with offline settings and machine identifiers
- [ ] `/data` contains media content
- [ ] Web UI accessible without sign-in
- [ ] Server ready for manual library configuration
- [ ] Media storage accessible for library creation
- [ ] Restart rebuilds everything correctly (stateless)

## ArgoCD sync commands

```bash
# Deploy/update Plex
argocd app sync plex

# Check deployment status
argocd app get plex

# Force refresh if needed
argocd app refresh plex
```

## Rollback procedure

If deployment fails, rollback via ArgoCD:

```bash
# Get previous revision
argocd app history plex

# Rollback to specific revision
argocd app rollback plex <revision-id>
```

Or revert Git changes and re-sync:

```bash
git revert <commit-hash>
git push
argocd app sync plex
```
