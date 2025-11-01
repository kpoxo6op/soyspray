# pihole

DNS filtering with wildcard resolution for *.soyspray.vip domains and ad filtering.

## Helm Inflate

Uses Helm inflate to apply values and dnsmasq configuration. Could not make Kustomize
post-renderer work, rolled back.

## DNS Configuration

Pi-hole uses dnsmasq wildcard rule for all *.soyspray.vip domains:
- `address=/soyspray.vip/192.168.1.20` - Resolves all subdomains to NGINX Ingress VIP
- No per-host DNS entries needed - managed automatically via Kubernetes Ingress

### Apply changes:
```bash
argocd app sync pihole && kubectl rollout restart deployment/pihole -n pihole
```

### Verify dnsmasq configuration:
```sh
POD=$(kubectl get pods -n pihole -l app=pihole -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n pihole $POD -- cat /etc/dnsmasq.d/02-custom.conf
```

### Test DNS resolution:
```sh
# Test wildcard resolution from Pi-hole
dig +short grafana.soyspray.vip @192.168.1.33
dig +short argocd.soyspray.vip @192.168.1.33
# Should return 192.168.1.20 (Ingress VIP)
```

## Adlists

See what lists the pod uses. Note how the pod did not pick up the last added entry `w3kbl.txt`

```sh
sqlite3 /etc/pihole/gravity.db "SELECT * FROM adlist"
1|https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts|1|1728723023|1728723023|Migrated from /etc/pihole/adlists.list|1729998265|118121|1|1
2|https://raw.githubusercontent.com/PolishFiltersTeam/KADhosts/master/KADhosts.txt|1|1728723023|1728723023|Migrated from /etc/pihole/adlists.list|1729998266|79718|0|2

cat /etc/pihole/adlists.list
https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts
https://raw.githubusercontent.com/PolishFiltersTeam/KADhosts/master/KADhosts.txt
https://v.firebog.net/hosts/static/w3kbl.txt
```

Delete PVC to apply new adlists

```sh
kubectl delete pvc pihole  -n pihole
kubectl patch pvc pihole -n pihole -p '{"metadata":{"finalizers":null}}'
kubectl delete po pihole-9f9f9d8f7-8p48t -n pihole
```

## Remove Password

```bash
kubectl exec -n pihole $(kubectl get pods -n pihole -l app=pihole -o jsonpath='{.items[0].metadata.name}') -- pihole -a -p
```

## `Switch-DNS`

Toggle DNS between Pi-hole and default on Windows.

```powershell
code $PROFILE
. $PROFILE
Switch-DNS -WhatIf
```

## Whitelists

Whitelists via volume mounts or values.yaml don't work.

Wait for pihole 6 to be released.

```sh
POD=$(kubectl get po -n pihole -l app=pihole -o jsonpath='{.items[0].metadata.name}')
kubectl exec -it $POD -n pihole -- pihole -w joyreactor.cc
kubectl exec -it $POD -n pihole -- pihole -w joyreactor.ru
kubectl exec -it $POD -n pihole -- pihole -w joyreactor.com
kubectl exec -it $POD -n pihole -- pihole -w reactor.cc
kubectl exec -it $POD -n pihole -- pihole -w t.co
```

## Testing Pi-Hole as DNS Server

Update Router DNS settings via mobile app

| Type      | IP               | Note          |
| --------- | ---------------- | ------------- |
| Primary   | 192.168.1.33     |  Pi Hole      |
| Secondary | 8.8.8.8          |  Google       |

Pi-hole DNS Configuration

| Domain                                         | IP               | Note          |
| ---------------------------------------------- | ---------------- | ------------- |
| *.soyspray.vip                                 | 192.168.1.20     | Wildcard via dnsmasq |
| [pihole.soyspray.vip](http://pihole.soyspray.vip/admin/login.php) | 192.168.1.20 | Via wildcard |

Looks like adding filters and not using secondary DNS helps.
