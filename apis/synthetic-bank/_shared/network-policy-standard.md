# NetworkPolicy Standard

Each tenant namespace allows ingress to the mock backend only from `platform-kong` Gateway pods on TCP 8080. Broad tenant-to-tenant ingress is not allowed.
