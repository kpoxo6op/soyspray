# Goal004 Security Controls

Kubernetes-native Kong OSS security controls for the synthetic bank APIs.

The static renderer emits Redis, NetworkPolicy, KongPlugin, HTTPRoute, and
KongConsumer resources. Runtime credential Secret manifests are rendered only
from local environment variables and are not committed.
