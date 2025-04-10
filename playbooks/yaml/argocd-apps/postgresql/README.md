# PostgreSQL

This directory holds the PostgreSQL ArgoCD app for Immich or other applications.

It uses the official Bitnami chart with a single replica, local user credentials,
and a 20Gi persistent volume. Values are in 'values.yaml', the application manifest
is in 'postgresql-application.yaml', and 'kustomization.yaml' orchestrates the Helm chart.

## PostgreSQL ArgoCD Application

- Namespace: postgresql
- Storage: 20Gi (Longhorn)
- Basic user/password: immich
- Hostname: postgresql-postgresql (Kubernetes service name)
- Database: immich

## Setup and Verification

1. Commit these files to the specified Git branch.
2. Let ArgoCD sync them automatically or trigger a manual sync.
3. Once synced, verify the pod status in the 'postgresql' namespace.
4. Confirm the “postgresql-postgresql” service is accessible from within the cluster.
5. Ensure the credentials and connection details are correct for any client application (like Immich).
