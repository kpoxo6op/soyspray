# Synthetic API Runtime State

Status: collected

Generated at: 2026-07-08T21:35:03+12:00

Kubernetes context: kubernetes-admin@cluster.local

## Tenant Namespaces
NAME                      STATUS   AGE
tenant-accounts           Active   27m
tenant-payments           Active   27m
tenant-cards              Active   27m
tenant-customer-profile   Active   27m
tenant-fraud              Active   27m
tenant-open-banking       Active   27m

## Deployments
NAMESPACE                 NAME                           READY   UP-TO-DATE   AVAILABLE   AGE
tenant-accounts           banklab-accounts-api           1/1     1            1           25m
tenant-cards              banklab-cards-api              1/1     1            1           25m
tenant-customer-profile   banklab-customer-profile-api   1/1     1            1           24m
tenant-fraud              banklab-fraud-decisions-api    1/1     1            1           24m
tenant-open-banking       banklab-open-banking-api       1/1     1            1           24m
tenant-payments           banklab-payments-api           1/1     1            1           25m

## Pods
NAMESPACE                 NAME                                            READY   STATUS    RESTARTS   AGE
tenant-accounts           banklab-accounts-api-57485b7d7d-dnv4j           1/1     Running   0          17m
tenant-cards              banklab-cards-api-64475cb8-t4tzn                1/1     Running   0          17m
tenant-customer-profile   banklab-customer-profile-api-8486ddb5fd-h6v24   1/1     Running   0          17m
tenant-fraud              banklab-fraud-decisions-api-5b55d88d4-kpqfn     1/1     Running   0          16m
tenant-open-banking       banklab-open-banking-api-d4866d7c4-s77q6        1/1     Running   0          16m
tenant-payments           banklab-payments-api-7f4b5c9df6-rzpxn           1/1     Running   0          17m

## Services
NAMESPACE                 NAME                           TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)   AGE
tenant-accounts           banklab-accounts-api           ClusterIP   10.233.19.122   <none>        80/TCP    25m
tenant-cards              banklab-cards-api              ClusterIP   10.233.23.232   <none>        80/TCP    25m
tenant-customer-profile   banklab-customer-profile-api   ClusterIP   10.233.20.168   <none>        80/TCP    24m
tenant-fraud              banklab-fraud-decisions-api    ClusterIP   10.233.41.87    <none>        80/TCP    24m
tenant-open-banking       banklab-open-banking-api       ClusterIP   10.233.5.125    <none>        80/TCP    24m
tenant-payments           banklab-payments-api           ClusterIP   10.233.27.167   <none>        80/TCP    25m

## ConfigMaps
NAMESPACE                 NAME                                      DATA   AGE
tenant-accounts           banklab-accounts-mock-responses           1      25m
tenant-cards              banklab-cards-mock-responses              1      25m
tenant-customer-profile   banklab-customer-profile-mock-responses   1      24m
tenant-fraud              banklab-fraud-decisions-mock-responses    1      24m
tenant-open-banking       banklab-open-banking-mock-responses       1      24m
tenant-payments           banklab-payments-mock-responses           1      25m

## HTTPRoutes
NAMESPACE                 NAME                       HOSTNAMES                       AGE
tenant-accounts           banklab-accounts           ["api.internal.banklab.test"]   25m
tenant-cards              banklab-cards              ["api.internal.banklab.test"]   25m
tenant-customer-profile   banklab-customer-profile   ["api.internal.banklab.test"]   24m
tenant-fraud              banklab-fraud-decisions    ["api.internal.banklab.test"]   24m
tenant-open-banking       banklab-open-banking       ["api.external.banklab.test"]   24m
tenant-payments           banklab-payments           ["api.internal.banklab.test"]   25m

## NetworkPolicies
NAMESPACE                 NAME                                 POD-SELECTOR                                          AGE
platform-kong             kong-allow-synthetic-api-upstreams   banklab.konghq.com/component=gateway                  8m37s
tenant-accounts           allow-kong-to-synthetic-api          app.kubernetes.io/name=banklab-accounts-api           25m
tenant-cards              allow-kong-to-synthetic-api          app.kubernetes.io/name=banklab-cards-api              24m
tenant-customer-profile   allow-kong-to-synthetic-api          app.kubernetes.io/name=banklab-customer-profile-api   24m
tenant-fraud              allow-kong-to-synthetic-api          app.kubernetes.io/name=banklab-fraud-decisions-api    24m
tenant-open-banking       allow-kong-to-synthetic-api          app.kubernetes.io/name=banklab-open-banking-api       23m
tenant-payments           allow-kong-to-synthetic-api          app.kubernetes.io/name=banklab-payments-api           25m

## Gateway API
NAME   CONTROLLER                          ACCEPTED   AGE   DESCRIPTION
kong   konghq.com/kic-gateway-controller   True       2d    
NAME            CLASS   ADDRESS         PROGRAMMED   AGE
kong-internal   kong    192.168.20.22   True         2d
kong-external   kong    192.168.20.22   True         2d

## Kong Services
NAME                         TYPE           CLUSTER-IP     EXTERNAL-IP     PORT(S)        AGE   SELECTOR
banklab-kong-gateway-proxy   LoadBalancer   10.233.33.79   192.168.20.22   80:30751/TCP   2d    app.kubernetes.io/component=app,app.kubernetes.io/instance=banklab-kong,app.kubernetes.io/name=gateway
