# pihole

Includes list of local DNS and ad filters source from configmaps

## Helm Inflate

Uses Helm inflate to apply configmap and values. Could not male  Kustomize
post-renderer work, rolled back.

## Custom DNS list

Pihole pod restart required to apply custom.list

location inside the pod

```sh
cat /etc/pihole/custom.list
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
| Primary   | 192.168.50.202   |  Pi Hole      |
| Secondary | 8.8.8.8          |  Google       |

Set Up Pi-hole to Handle Local DNS Entries

| Domain                                         | IP               | Note          |
| ---------------------------------------------- | ---------------- | ------------- |
| [argocd.lan](http://argocd.lan/applications)   | 192.168.50.201   |               |
| [pihole.lan](http://pihole.lan/admin/login.php)| 192.168.50.202   |               |

Looks like adding filters and not using secondary DNS helps.
