# Goal004 Security Runtime State

Status: pass

Supported states: not run, pass, fail, blocked, partial

Generated at: 2026-07-09T00:16:07+12:00

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
tenant-accounts           banklab-acl              acl              79m
tenant-accounts           banklab-correlation-id   correlation-id   79m
tenant-accounts           banklab-key-auth         key-auth         79m
tenant-accounts           banklab-rate-limit       rate-limiting    79m
tenant-cards              banklab-acl              acl              78m
tenant-cards              banklab-correlation-id   correlation-id   77m
tenant-cards              banklab-key-auth         key-auth         78m
tenant-cards              banklab-rate-limit       rate-limiting    77m
tenant-customer-profile   banklab-acl              acl              77m
tenant-customer-profile   banklab-correlation-id   correlation-id   77m
tenant-customer-profile   banklab-key-auth         key-auth         77m
tenant-customer-profile   banklab-rate-limit       rate-limiting    77m
tenant-fraud              banklab-acl              acl              76m
tenant-fraud              banklab-correlation-id   correlation-id   76m
tenant-fraud              banklab-key-auth         key-auth         76m
tenant-fraud              banklab-rate-limit       rate-limiting    76m
tenant-open-banking       banklab-acl              acl              76m
tenant-open-banking       banklab-correlation-id   correlation-id   75m
tenant-open-banking       banklab-jwt              jwt              76m
tenant-open-banking       banklab-rate-limit       rate-limiting    75m
tenant-payments           banklab-acl              acl              78m
tenant-payments           banklab-correlation-id   correlation-id   78m
tenant-payments           banklab-key-auth         key-auth         78m
tenant-payments           banklab-rate-limit       rate-limiting    78m

## KongConsumers
NAME                       USERNAME                   AGE   PROGRAMMED
external-fintech-partner   external-fintech-partner   74m   True
fraud-platform             fraud-platform             74m   True
internal-crm               internal-crm               75m   True
internet-banking-web       internet-banking-web       75m   True
mobile-banking-app         mobile-banking-app         75m   True
payments-processor         payments-processor         75m   True

## Credential Secret Names
NAME                                                TYPE     DATA   AGE
banklab-external-fintech-partner-jwt                Opaque   3      80m
banklab-external-fintech-partner-open-banking-acl   Opaque   1      79m
banklab-fraud-platform-fraud-decisions-acl          Opaque   1      80m
banklab-fraud-platform-key-auth                     Opaque   1      80m
banklab-internal-crm-customer-profile-acl           Opaque   1      80m
banklab-internal-crm-key-auth                       Opaque   1      80m
banklab-internet-banking-web-cards-acl              Opaque   1      80m
banklab-internet-banking-web-key-auth               Opaque   1      81m
banklab-mobile-banking-app-accounts-acl             Opaque   1      81m
banklab-mobile-banking-app-key-auth                 Opaque   1      81m
banklab-payments-processor-key-auth                 Opaque   1      81m
banklab-payments-processor-payments-acl             Opaque   1      81m

Secret values are intentionally not printed.
