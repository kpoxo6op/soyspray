# Immich Application Configuration

This document outlines the configuration and verification steps for the Immich application deployed via ArgoCD.

## Overview

- **Deployment:** Managed by ArgoCD application `immich`.
- **Namespace:** `immich`
- **Chart:** Official Immich Helm chart (`immich-app/immich`)
- **Configuration:** Uses Helm with Kustomize post-rendering.
- **Storage:** Requires a manually defined PersistentVolumeClaim (`immich-library`) using `longhorn` StorageClass. The PVC definition is included via Kustomize.
- **Ingress:** Exposed via `nginx` Ingress Controller at `https://immich.soyspray.vip`.
- **TLS:** Handled by `cert-manager` using `letsencrypt-production` ClusterIssuer and the `prod-cert-tls` secret (synced from `cert-manager` namespace).
- **Dependencies:** Assumes external PostgreSQL and Redis (bundled ones disabled in `values.yaml`).

## Key Files

- `immich-application.yaml`: ArgoCD Application manifest.
- `values.yaml`: Helm chart values overrides (ingress, persistence claim reference, resource limits, etc.).
- `kustomization.yaml`: Kustomize config to include the PVC and set the namespace.
- `immich-library-pvc.yaml`: Manifest defining the required `immich-library` PersistentVolumeClaim.

## Verification Checklist (After Deployment/Sync)

1. **Check ArgoCD Status:**

    ```bash
    argocd app get immich -n argocd
    ```

    *Look for `Synced` and `Healthy` status.*

2. **Check Namespace Resources:**

    ```bash
    kubectl get all -n immich
    ```

    *Verify Deployments, Services, Pods, Ingress, PVC are present.*

3. **Check Persistent Volume Claim (PVC):**

    ```bash
    kubectl get pvc -n immich immich-library
    ```

    *Ensure `STATUS` is `Bound`.*

4. **Check Pod Status:**

    ```bash
    kubectl get pods -n immich
    ```

    *Ensure `immich-server-...` pod (and `immich-machine-learning-...` if enabled) shows `Running` and `READY 1/1` (or similar).*

5. **Verify Applied Resource Limits (Example for server):**

    ```bash
    # Get the specific pod name first with 'kubectl get pods -n immich'
    kubectl describe pod <immich-server-pod-name> -n immich
    ```

    *Look for the `Resources:` section under Containers to confirm applied limits/requests.*

6. **Check Server Logs:**

    ```bash
    kubectl logs deploy/immich-server -n immich -f
    ```

    *Look for successful startup messages, database connections, and absence of critical errors.*

7. **Check Ingress Status:**

    ```bash
    kubectl get ingress -n immich
    ```

    *Verify an ADDRESS is assigned (usually the Nginx controller's LoadBalancer IP).*

    ```bash
    # Get the specific ingress name first with 'kubectl get ingress -n immich'
    kubectl describe ingress <immich-ingress-name> -n immich
    ```

    *Check rules route `immich.soyspray.vip` correctly and the `TLS` section references `prod-cert-tls`.*

8. **Check TLS Secret:**

    ```bash
    kubectl get secret prod-cert-tls -n immich
    ```

    *Confirm the secret exists in the `immich` namespace (synced by `sync-certificates.yml` playbook).*

9. **Check DNS Resolution:**

    ```bash
    nslookup immich.soyspray.vip
    ```

    *Verify it resolves to the correct LoadBalancer IP address of your Nginx Ingress.* (May require waiting for DNS propagation).

10. **Access Web UI:**
    - Open `https://immich.soyspray.vip` in your browser.
    - *Expect a valid TLS certificate (no warnings) and the Immich login/setup page to load.*
