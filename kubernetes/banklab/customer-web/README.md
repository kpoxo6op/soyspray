# Customer web demo

This package provides a small browser interface and a background traffic
generator. Both make gateway behaviour visible without requiring a separate
client repository.

| Area | Files |
| --- | --- |
| Browser application | [`app/`](app/) |
| Web deployment | [`deployment.yaml`](deployment.yaml), [`service.yaml`](service.yaml), [`ingress.yaml`](ingress.yaml) |
| Synthetic requests | [`traffic-clients.yaml`](traffic-clients.yaml), [`traffic-networkpolicy.yaml`](traffic-networkpolicy.yaml) |
| Network boundary | [`networkpolicy.yaml`](networkpolicy.yaml) |
| Package entry point | [`kustomization.yaml`](kustomization.yaml) |

The background client sends both permitted and rejected requests so the
dashboard has useful traffic after startup.
