# Synthetic API Runtime Evidence

Status: pass

Supported states: not run, pass, fail, blocked, partial

Generated at: 2026-07-08T23:14:10+12:00

Kubernetes context: kubernetes-admin@cluster.local

## Checks
accounts namespace: pass
accounts deployment ready: pass
accounts HTTPRoute present: pass
payments namespace: pass
payments deployment ready: pass
payments HTTPRoute present: pass
cards namespace: pass
cards deployment ready: pass
cards HTTPRoute present: pass
customer-profile namespace: pass
customer-profile deployment ready: pass
customer-profile HTTPRoute present: pass
fraud-decisions namespace: pass
fraud-decisions deployment ready: pass
fraud-decisions HTTPRoute present: pass
open-banking namespace: pass
open-banking deployment ready: pass
open-banking HTTPRoute present: pass

## Synthetic API Namespaces
NAME                      STATUS   AGE
tenant-accounts           Active   127m
tenant-payments           Active   127m
tenant-cards              Active   127m
tenant-customer-profile   Active   127m
tenant-fraud              Active   127m
tenant-open-banking       Active   127m

## Synthetic API Pods
NAMESPACE                 NAME                                            READY   STATUS    RESTARTS   AGE
tenant-accounts           banklab-accounts-api-57485b7d7d-dnv4j           1/1     Running   0          116m
tenant-cards              banklab-cards-api-64475cb8-t4tzn                1/1     Running   0          116m
tenant-customer-profile   banklab-customer-profile-api-8486ddb5fd-h6v24   1/1     Running   0          116m
tenant-fraud              banklab-fraud-decisions-api-5b55d88d4-kpqfn     1/1     Running   0          116m
tenant-open-banking       banklab-open-banking-api-d4866d7c4-s77q6        1/1     Running   0          115m
tenant-payments           banklab-payments-api-7f4b5c9df6-rzpxn           1/1     Running   0          116m

## Synthetic API HTTPRoutes
NAMESPACE                 NAME                       HOSTNAMES                       AGE
tenant-accounts           banklab-accounts           ["api.internal.banklab.test"]   124m
tenant-cards              banklab-cards              ["api.internal.banklab.test"]   124m
tenant-customer-profile   banklab-customer-profile   ["api.internal.banklab.test"]   123m
tenant-fraud              banklab-fraud-decisions    ["api.internal.banklab.test"]   123m
tenant-open-banking       banklab-open-banking       ["api.external.banklab.test"]   123m
tenant-payments           banklab-payments           ["api.internal.banklab.test"]   124m
