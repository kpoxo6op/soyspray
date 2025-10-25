# Check Jobs

## Overview

Check status of all automated backup jobs, cron schedules, and their execution logs without creating manual jobs or redeploying anything.

## Database Backup System (CNPG)

### 1. Check Scheduled Backup Configuration
```bash
kubectl get scheduledbackup -n postgresql
```

### 2. Check Cluster Backup Status
```bash
kubectl describe cluster -n postgresql immich-db | grep -A 3 -B 1 "ContinuousArchiving\|Backup\|backup"
```

### 3. Check Backup Secrets
```bash
kubectl get secrets -n postgresql | grep immich-offsite
```

### 4. Check Backup Objects and History
```bash
kubectl get backup.postgresql.cnpg.io -n postgresql
```

### 5. Check CNPG Operator Status
```bash
kubectl get pods -n cnpg-system
```

## Media Backup System

### 1. Check CronJob Status
```bash
kubectl get cronjobs -n immich
```

### 2. Check CronJob Details
```bash
kubectl get cronjob -n immich immich-media-offsite-sync -o yaml | grep -A 3 -B 3 "schedule\|suspend\|lastScheduleTime\|lastSuccessfulTime"
```

### 3. Check Job History
```bash
kubectl get jobs -n immich
```

### 4. Check Backup Secrets
```bash
kubectl get secrets -n immich | grep immich-offsite
```

### 5. Check ServiceAccount and ConfigMap
```bash
kubectl get serviceaccount,configmap -n immich | grep immich-offsite
```

## Alias Service Status

### 1. Check Database Alias Service
```bash
kubectl get svc -n postgresql immich-db-active
```

### 2. Verify Immich Connection
```bash
kubectl exec -n immich deployment/immich-server -- env | grep DB_URL
```

## ArgoCD Application Status

### 1. Check Database Application
```bash
argocd app get immich-db | grep -E "(Sync Status|Health Status|targetRevision)"
```

### 2. Check Media Backup Application
```bash
argocd app get immich-offsite-backup | grep -E "(Sync Status|Health Status|targetRevision)"
```

### 3. Check Application Resources
```bash
argocd app get immich-db -o yaml | grep -A 5 "GROUP\|KIND\|NAME\|STATUS\|HEALTH"
argocd app get immich-offsite-backup -o yaml | grep -A 5 "GROUP\|KIND\|NAME\|STATUS\|HEALTH"
```

## Logs and Recent Activity

### 1. Check Recent Events
```bash
kubectl get events -n postgresql --sort-by='.lastTimestamp' | tail -10
kubectl get events -n immich --sort-by='.lastTimestamp' | tail -10
```

### 2. Check CronJob Logs (if jobs exist)
```bash
# Get recent job names
JOBS=$(kubectl get jobs -n immich -o jsonpath='{.items[*].metadata.name}' | tr ' ' '\n' | tail -3)

for job in $JOBS; do
  echo "=== Logs for job: $job ==="
  kubectl logs -n immich job/$job 2>/dev/null || echo "No logs available for $job"
done
```

### 3. Check CNPG Operator Logs (if issues detected)
```bash
kubectl logs -n cnpg-system deployment/cnpg-operator-cloudnative-pg --tail=20
```

## Validation Checks

### 1. Verify Backup Schedules Are Active
```bash
# Database backup should show LAST BACKUP timestamp
kubectl get scheduledbackup -n postgresql immich-db-daily

# Media backup should show recent lastScheduleTime and lastSuccessfulTime
kubectl get cronjob -n immich immich-media-offsite-sync -o yaml | grep -E "lastScheduleTime|lastSuccessfulTime"
```

### 2. Verify No Manual/Test Jobs Exist
```bash
# Should return no results or only automated jobs
kubectl get jobs -n postgresql
kubectl get jobs -n immich | grep -v "Complete.*immich-media-offsite-sync"
```

### 3. Verify Continuous Archiving
```bash
kubectl describe cluster -n postgresql immich-db | grep -A 2 "ContinuousArchiving"
```

## Quick Status Summary
```bash
echo "=== BACKUP SYSTEMS STATUS ==="
echo "Database Scheduled Backup:"
kubectl get scheduledbackup -n postgresql
echo -e "\nMedia CronJob:"
kubectl get cronjobs -n immich
echo -e "\nDatabase Alias:"
kubectl get svc -n postgresql immich-db-active
echo -e "\nArgoCD Applications:"
argocd app get immich-db | grep -E "(Sync Status|Health Status)"
argocd app get immich-offsite-backup | grep -E "(Sync Status|Health Status)"
echo -e "\nRecent Backup Activity:"
kubectl get backup.postgresql.cnpg.io -n postgresql 2>/dev/null || echo "No backup objects found"
kubectl get jobs -n immich | grep -E "(Complete|Running)" || echo "No media jobs found"
```
