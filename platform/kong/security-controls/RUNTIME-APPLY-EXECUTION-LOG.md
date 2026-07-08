# Goal004 Security Runtime Apply Execution Log

Status: pass

Supported states: not run, pass, fail, blocked, partial

Command: make goal004-security-apply

Timestamp: 2026-07-09T00:14:00+12:00

Kubernetes context: kubernetes-admin@cluster.local

## Output
namespace/synthetic-clients unchanged
deployment.apps/banklab-rate-limit-redis unchanged
service/banklab-rate-limit-redis unchanged
networkpolicy.networking.k8s.io/banklab-rate-limit-redis-ingress unchanged
networkpolicy.networking.k8s.io/kong-allow-rate-limit-redis unchanged
networkpolicy.networking.k8s.io/kong-allow-node-local-dns unchanged
networkpolicy.networking.k8s.io/kong-allow-controller-webhook-from-api-server unchanged
kongplugin.configuration.konghq.com/banklab-key-auth unchanged
kongplugin.configuration.konghq.com/banklab-acl unchanged
kongplugin.configuration.konghq.com/banklab-rate-limit unchanged
kongplugin.configuration.konghq.com/banklab-correlation-id unchanged
kongplugin.configuration.konghq.com/banklab-key-auth unchanged
kongplugin.configuration.konghq.com/banklab-acl unchanged
kongplugin.configuration.konghq.com/banklab-rate-limit unchanged
kongplugin.configuration.konghq.com/banklab-correlation-id unchanged
kongplugin.configuration.konghq.com/banklab-key-auth unchanged
kongplugin.configuration.konghq.com/banklab-acl unchanged
kongplugin.configuration.konghq.com/banklab-rate-limit unchanged
kongplugin.configuration.konghq.com/banklab-correlation-id unchanged
kongplugin.configuration.konghq.com/banklab-key-auth unchanged
kongplugin.configuration.konghq.com/banklab-acl unchanged
kongplugin.configuration.konghq.com/banklab-rate-limit unchanged
kongplugin.configuration.konghq.com/banklab-correlation-id unchanged
kongplugin.configuration.konghq.com/banklab-key-auth unchanged
kongplugin.configuration.konghq.com/banklab-acl unchanged
kongplugin.configuration.konghq.com/banklab-rate-limit unchanged
kongplugin.configuration.konghq.com/banklab-correlation-id unchanged
kongplugin.configuration.konghq.com/banklab-jwt unchanged
kongplugin.configuration.konghq.com/banklab-acl unchanged
kongplugin.configuration.konghq.com/banklab-rate-limit unchanged
kongplugin.configuration.konghq.com/banklab-correlation-id unchanged
kongconsumer.configuration.konghq.com/mobile-banking-app unchanged
kongconsumer.configuration.konghq.com/payments-processor unchanged
kongconsumer.configuration.konghq.com/internet-banking-web unchanged
kongconsumer.configuration.konghq.com/internal-crm unchanged
kongconsumer.configuration.konghq.com/fraud-platform unchanged
kongconsumer.configuration.konghq.com/external-fintech-partner unchanged
httproute.gateway.networking.k8s.io/banklab-accounts configured
httproute.gateway.networking.k8s.io/banklab-payments configured
httproute.gateway.networking.k8s.io/banklab-cards configured
httproute.gateway.networking.k8s.io/banklab-customer-profile configured
httproute.gateway.networking.k8s.io/banklab-fraud-decisions configured
httproute.gateway.networking.k8s.io/banklab-open-banking configured
