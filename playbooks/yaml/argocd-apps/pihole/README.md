# pihole

includes list of local DNS and ad filters source from configmaps

## Custom DNS list

Pihole pod restart required to apply custom.list

location inside the pod

```sh
cat /etc/pihole/custom.list
```

## Adlists

See what lists the pod uses. Note how the pod did not pick up the last added entry

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
