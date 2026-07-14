# Kong Bank Lab

This lab runs Kong OSS as a small banking API platform on the Soyspray cluster.
It is built for learning and day-to-day operation, not as a slideware demo.

## What is running

| Layer | Runtime |
| --- | --- |
| Gateway | Two Kong OSS data-plane pods with Kong Ingress Controller |
| Routing | Kubernetes Gateway API with internal and external gateways |
| APIs | Accounts, payments, cards, customer profile, fraud decisions, and open banking |
| Clients | A customer web app plus background mobile, payments, CRM, and fraud traffic |
| Controls | Key Auth or JWT, ACLs, Redis-backed rate limits, correlation IDs, and NetworkPolicy |
| Operations | Argo CD applications, Prometheus metrics, Loki logs, and a Grafana dashboard |

## Open the lab

- [Customer app](http://banklab-web.soyspray.vip)
- [Gateway dashboard](https://grafana.soyspray.vip/d/kong-bank-lab-operator-overview/kong-bank-lab-gateway-operator-overview)
- [Argo CD](https://argocd.soyspray.vip)

These addresses are private to the home network and its Tailscale route.

## First commands

```sh
make check    # local tests, manifests, and docs
make status   # cluster and Argo health
make smoke    # read-only API checks
```

Go to [Get started](getting-started.md) for local setup. Operators should keep
the [verification runbook](runbooks/verify.md) close when changing the lab.
