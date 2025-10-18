# Test: ImmichMediaBackupFailureImmediate Alert

## Setup Port Forward

```bash
kubectl port-forward -n monitoring svc/loki 3100:3100 &
```

## Trigger Failure

Patch secret with invalid credentials:

```bash
kubectl patch secret immich-offsite-writer -n immich --type='json' \
  -p='[{"op": "replace", "path": "/data/AWS_ACCESS_KEY_ID", "value": "'$(echo -n "INVALID_KEY" | base64)'"}]'
```

Create manual job:

```bash
kubectl create job --from=cronjob/immich-media-offsite-sync immich-test-error-$(date +%s) -n immich
```

## Verify Ingestion

Wait 30 seconds for log ingestion, then query Loki:

```bash
curl -G -s 'http://localhost:3100/loki/api/v1/query_range' \
  --data-urlencode 'query={namespace="immich", container="aws-sync", job="kubernetes-pods"} |= "error"' \
  --data-urlencode 'start='$(date -d '10 minutes ago' +%s)000000000 \
  --data-urlencode 'end='$(date +%s)000000000 \
  | jq '.data.result[] | {pod: .stream.pod, lines: (.values | length)}'
```

Expected: Pod logs with error lines

Run alert query:

```bash
curl -G -s 'http://localhost:3100/loki/api/v1/query' \
  --data-urlencode 'query=sum by (namespace) (count_over_time({namespace="immich", container="aws-sync"} |~ "(?i)(an error occurred \\(|error|accessdenied|expiredtoken|slowdown|requesttimetoo skewed|read-only file system|connection reset)" [5m]))' \
  | jq '.data.result[].value[1]'
```

Expected: Non-zero count

## Verify Alert

Wait 2 minutes for alert to fire, then check Telegram for ImmichMediaBackupFailureImmediate notification.
