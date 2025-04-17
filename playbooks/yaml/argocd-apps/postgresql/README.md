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

To verify the setup:

1. Check the pod and service status in the `postgresql` namespace:

   ```bash
   kubectl get pods -n postgresql
   kubectl get svc -n postgresql
   ```

2. Test the connection to the database using the `immich` user from within the pod:

   ```bash
   kubectl exec -n postgresql postgresql-0 -- sh -c 'env PGPASSWORD=immich psql -U immich -d immich -h localhost -c "\\conninfo"'
   ```

   You should see a message confirming the connection.

3. Test the service

```sh
kubectl run pg-test --rm -it --restart=Never --image=postgres:14 -- bash -c "PGPASSWORD=immich psql -h postgresql.postgresql.svc.cluster.local -U immich -d immich -c 'SELECT 1;'"
```
