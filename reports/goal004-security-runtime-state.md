# Goal004 Security Runtime State

Status: pass

Supported states: not run, pass, fail, blocked, partial

Generated at: 2026-07-08T23:14:12+12:00

Kubernetes context: kubernetes-admin@cluster.local

Credential source: runtime-generated-not-committed

## Checks
KongPlugin count: pass; count=24
KongConsumer count: pass; count=6
credential Secret count: pass; count=12; values-not-printed
accounts route plugins: pass
payments route plugins: pass
cards route plugins: pass
customer-profile route plugins: pass
fraud-decisions route plugins: pass
open-banking route plugins: pass

## KongPlugins
NAMESPACE                 NAME                     PLUGIN-TYPE      AGE   PROGRAMMED
tenant-accounts           banklab-acl              acl              17m   
tenant-accounts           banklab-correlation-id   correlation-id   17m   
tenant-accounts           banklab-key-auth         key-auth         17m   
tenant-accounts           banklab-rate-limit       rate-limiting    17m   
tenant-cards              banklab-acl              acl              16m   
tenant-cards              banklab-correlation-id   correlation-id   15m   
tenant-cards              banklab-key-auth         key-auth         16m   
tenant-cards              banklab-rate-limit       rate-limiting    16m   
tenant-customer-profile   banklab-acl              acl              15m   
tenant-customer-profile   banklab-correlation-id   correlation-id   15m   
tenant-customer-profile   banklab-key-auth         key-auth         15m   
tenant-customer-profile   banklab-rate-limit       rate-limiting    15m   
tenant-fraud              banklab-acl              acl              14m   
tenant-fraud              banklab-correlation-id   correlation-id   14m   
tenant-fraud              banklab-key-auth         key-auth         15m   
tenant-fraud              banklab-rate-limit       rate-limiting    14m   
tenant-open-banking       banklab-acl              acl              14m   
tenant-open-banking       banklab-correlation-id   correlation-id   13m   
tenant-open-banking       banklab-jwt              jwt              14m   
tenant-open-banking       banklab-rate-limit       rate-limiting    13m   
tenant-payments           banklab-acl              acl              16m   
tenant-payments           banklab-correlation-id   correlation-id   16m   
tenant-payments           banklab-key-auth         key-auth         17m   
tenant-payments           banklab-rate-limit       rate-limiting    16m   

## KongConsumers
NAME                       USERNAME                   AGE   PROGRAMMED
external-fintech-partner   external-fintech-partner   12m   True
fraud-platform             fraud-platform             12m   True
internal-crm               internal-crm               13m   True
internet-banking-web       internet-banking-web       13m   True
mobile-banking-app         mobile-banking-app         13m   True
payments-processor         payments-processor         13m   True

## Credential Secret Names
NAME                                                TYPE     DATA   AGE
banklab-external-fintech-partner-jwt                Opaque   3      18m
banklab-external-fintech-partner-open-banking-acl   Opaque   1      18m
banklab-fraud-platform-fraud-decisions-acl          Opaque   1      18m
banklab-fraud-platform-key-auth                     Opaque   1      18m
banklab-internal-crm-customer-profile-acl           Opaque   1      18m
banklab-internal-crm-key-auth                       Opaque   1      18m
banklab-internet-banking-web-cards-acl              Opaque   1      19m
banklab-internet-banking-web-key-auth               Opaque   1      19m
banklab-mobile-banking-app-accounts-acl             Opaque   1      19m
banklab-mobile-banking-app-key-auth                 Opaque   1      19m
banklab-payments-processor-key-auth                 Opaque   1      19m
banklab-payments-processor-payments-acl             Opaque   1      19m

Secret values are intentionally not printed.
