# qBittorrent (Raw K8s Manifests)

qBittorrent downloads and seeds into `/downloads` on `node-0`. The web UI is
<https://torrent.soyspray.vip> behind Authentik; the native API stays on
`/api/v2`.

admin / 123

This folder contains a minimal raw Kubernetes definition of qBittorrent,
including:

1. Namespace `media`
2. PVCs for config and downloads
3. A Deployment with environment variables and resource limits
4. A ClusterIP web UI Service behind the ingress
5. The `qbittorrent-peers` LoadBalancer at 192.168.20.30, TCP and UDP 49160
6. `qBittorrent.conf`, copied over the live config at every pod start

The `media-downloads` claim is bound to a static local PersistentVolume at
`/srv/media/downloads` on `node-0`. Prepare and mount the USB disk on the host
before syncing this app.

## Peer port

Mercury gives the home connection a static public IPv4 address. OpenWrt gets
it by DHCP on VLAN 10 (`network.wan.proto='dhcp'`, device `eth0.10`); the old
PPPoE login only returns a shared CGNAT address. The router forwards the peer
port to the LoadBalancer, which keeps real peer addresses
(`externalTrafficPolicy: Local`):

```sh
ssh openwrt '
uci set firewall.qbittorrent_k8s=redirect
uci set firewall.qbittorrent_k8s.name=qbittorrent-k8s
uci set firewall.qbittorrent_k8s.src=wan
uci set firewall.qbittorrent_k8s.src_dport=49160
uci set firewall.qbittorrent_k8s.dest=lan
uci set firewall.qbittorrent_k8s.dest_ip=192.168.20.30
uci set firewall.qbittorrent_k8s.dest_port=49160
uci set firewall.qbittorrent_k8s.proto="tcp udp"
uci set firewall.qbittorrent_k8s.family=ipv4
uci set firewall.qbittorrent_k8s.target=DNAT
uci commit firewall && fw4 check && /etc/init.d/firewall reload'
```

Back up the router first with `sysupgrade -b` into the ignored
`.router-backups/` folder. Trackers see the static address as the source of
announces, so `qBittorrent.conf` sets no announce IP.

## Checks

```sh
kubectl -n media get svc qbittorrent-peers     # EXTERNAL-IP 192.168.20.30
ssh openwrt 'ifstatus wan | jsonfilter -e "@[\"ipv4-address\"][0].address"'
curl -s -4 https://portcheck.transmissionbt.com/49160; echo   # 1 = open from outside
```

Keep `-4`: on the dual-stack LAN the checker otherwise tests the laptop's IPv6
address and reports 0. The Peers tab of a seeding torrent lists inbound peers
with the `I` flag (`I P` over uTP). The green status icon is not proof, because
uTP hole punching turned it green even behind CGNAT.

## Create a password hash

```python
python - "MySuperSecret1!" <<'PY'
import os, sys, base64, hashlib
pwd = sys.argv[1].encode()
salt = os.urandom(16)
dk   = hashlib.pbkdf2_hmac('sha512', pwd, salt, 100000)
print(f'@ByteArray({base64.b64encode(salt).decode()}:{base64.b64encode(dk).decode()})')
PY

sha256:5000:b9040da26fc5cfb8:32d63d47b37f03ac6d716bb3a2d932c6a5c43c8b69215444e0588928fae9eae7
```

## Booklore Integration

qBittorrent integrates with Booklore via filesystem. The `books` category downloads to `/downloads/books`.

### Direct Library Indexing (Recommended)

No script needed. Booklore mounts the same PVC and indexes `/downloads/books` as a Library.

## Delete the app manually

Delete from argocd

```sh
kubectl patch application qbittorrent -n argocd -p '{"metadata":{"finalizers":[]}}' --type=merge
kubectl delete deployment qbittorrent -n media
kubectl delete job qbittorrent-bootstrap -n media
kubectl delete service qbittorrent qbittorrent-peers -n media
kubectl delete configmap -n media -l app=qbittorrent
kubectl delete ingress qbittorrent-ingress -n media
kubectl delete pvc qbittorrent-config media-downloads -n media
```
