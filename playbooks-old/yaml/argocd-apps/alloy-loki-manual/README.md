# Grafana Loki + Grafana Alloy

This application deploys a single-binary Grafana Loki instance with
persistent storage alongside Grafana Alloy agents that run on every node.
It provides cluster-wide log collection, aggregation, querying from
Grafana, and alerting routed through the existing Alertmanager stack.

## Why Manual Deployment

Currently using manual deployment instead of operators because the Loki operator requires S3-compatible object storage. Migration to operator-based approach is tracked in:
- https://github.com/kpoxo6op/soyspray/issues/83 (Install more RAM)
- https://github.com/kpoxo6op/soyspray/issues/84 (Deploy MinIO object storage)
- https://github.com/kpoxo6op/soyspray/issues/85 (Migrate to operators)
