# Loki Operator Stack

This application deploys Loki using the Loki Operator with S3-backed storage.

## Prerequisites

**REQUIRED**: Create the object storage Secret before deploying:

```bash
kubectl -n monitoring create secret generic loki-object-storage \
  --from-literal=bucketnames=loki \
  --from-literal=endpoint=http://object-storage.monitoring.svc.cluster.local:9000 \
  --from-literal=access_key_id='minioadmin' \
  --from-literal=access_key_secret='minioadmin' \
  --from-literal=region='us-east-1'
```

**IMPORTANT**: Update `access_key_id` and `access_key_secret` to match your MinIO credentials from `object-storage-credentials` Secret.

**ALSO REQUIRED**: Create the `loki` bucket in MinIO before LokiStack starts. The operator will not create it automatically.

## Post-Deployment Steps

After the operator creates the LokiStack, verify the gateway service name:

```bash
kubectl get svc -n monitoring | grep loki
```

Update `loki-externalname-service.yaml` if the gateway service name differs from `loki-gateway-http`.

## Components

- **loki-operator-application.yaml**: Deploys the Loki Operator (wave 1)
- **loki-application.yaml**: Deploys Loki CRs (wave 2)
- **lokistack.yaml**: LokiStack CR with S3 storage configuration
- **rulerconfig.yaml**: Ruler configuration for Alertmanager integration
- **loki-alerting-rules.yaml**: AlertingRule CRs for log-based alerts
- **loki-externalname-service.yaml**: ExternalName service pointing to gateway (write path)
- **loki-servicemonitor.yaml**: Prometheus scraping configuration

## Storage

- Uses S3-compatible storage (MinIO)
- Retention: 14 days
- Schema: v13 (TSDB)

