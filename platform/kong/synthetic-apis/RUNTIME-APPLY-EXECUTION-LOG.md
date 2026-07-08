# Synthetic API Runtime Apply Execution Log

Status: pass

Supported states: not run, pass, fail, blocked, partial

Command: make synthetic-api-apply

Timestamp: 2026-07-08T21:35:00+12:00

Kubernetes context: kubernetes-admin@cluster.local

## Output
networkpolicy.networking.k8s.io/kong-allow-synthetic-api-upstreams unchanged
configmap/banklab-accounts-mock-responses unchanged
deployment.apps/banklab-accounts-api unchanged
service/banklab-accounts-api unchanged
httproute.gateway.networking.k8s.io/banklab-accounts configured
networkpolicy.networking.k8s.io/allow-kong-to-synthetic-api unchanged
configmap/banklab-payments-mock-responses unchanged
deployment.apps/banklab-payments-api unchanged
service/banklab-payments-api unchanged
httproute.gateway.networking.k8s.io/banklab-payments configured
networkpolicy.networking.k8s.io/allow-kong-to-synthetic-api unchanged
configmap/banklab-cards-mock-responses unchanged
deployment.apps/banklab-cards-api unchanged
service/banklab-cards-api unchanged
httproute.gateway.networking.k8s.io/banklab-cards configured
networkpolicy.networking.k8s.io/allow-kong-to-synthetic-api unchanged
configmap/banklab-customer-profile-mock-responses unchanged
deployment.apps/banklab-customer-profile-api unchanged
service/banklab-customer-profile-api unchanged
httproute.gateway.networking.k8s.io/banklab-customer-profile configured
networkpolicy.networking.k8s.io/allow-kong-to-synthetic-api unchanged
configmap/banklab-fraud-decisions-mock-responses unchanged
deployment.apps/banklab-fraud-decisions-api unchanged
service/banklab-fraud-decisions-api unchanged
httproute.gateway.networking.k8s.io/banklab-fraud-decisions configured
networkpolicy.networking.k8s.io/allow-kong-to-synthetic-api unchanged
configmap/banklab-open-banking-mock-responses unchanged
deployment.apps/banklab-open-banking-api unchanged
service/banklab-open-banking-api unchanged
httproute.gateway.networking.k8s.io/banklab-open-banking configured
networkpolicy.networking.k8s.io/allow-kong-to-synthetic-api unchanged
