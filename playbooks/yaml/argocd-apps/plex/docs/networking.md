# Networking

## End‑to‑end data path

```text
[ Remote Plex App ]
          |
          v
   (HTTPS handshake via plex.tv for discovery)
          |
          v
[ Internet ] -----> [ WAN:116.251.193.233 | eero NAT ]
                                 |
                       Port Forward TCP 32400
                                 |
                                 v
                    [ 192.168.50.103 | node-0 ]
                                 |
                     NodePort 32400 (kube-proxy)
                                 |
                                 v
                     [ Service: plex (32400) ]
                                 |
                                 v
                     [ Pod: linuxserver/plex ]
```
