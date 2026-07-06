# Kong Runtime Evidence

Generated at: 2026-07-06T21:23:47+12:00

Kubernetes context: kubernetes-admin@cluster.local

## Namespaces
NAME                  STATUS   AGE
platform-kong         Active   27m
platform-kong-smoke   Active   27m

## Kong Pods
NAME                                       READY   STATUS    RESTARTS      AGE   LABELS
banklab-kong-controller-6b67f44db8-rhs5j   1/1     Running   8 (11m ago)   27m   app.kubernetes.io/component=app,app.kubernetes.io/instance=banklab-kong,app.kubernetes.io/managed-by=Helm,app.kubernetes.io/name=controller,app.kubernetes.io/version=3.9,app=banklab-kong-controller,banklab.konghq.com/component=kic,banklab.konghq.com/platform-layer=gateway,helm.sh/chart=controller-3.2.0,pod-template-hash=6b67f44db8,version=3.9
banklab-kong-gateway-75b48d447c-wbskb      1/1     Running   0             27m   app.kubernetes.io/component=app,app.kubernetes.io/instance=banklab-kong,app.kubernetes.io/managed-by=Helm,app.kubernetes.io/name=gateway,app.kubernetes.io/version=3.9,app=banklab-kong-gateway,banklab.konghq.com/component=gateway,banklab.konghq.com/platform-layer=gateway,helm.sh/chart=gateway-3.2.0,pod-template-hash=75b48d447c,version=3.9
banklab-kong-gateway-75b48d447c-xgf87      1/1     Running   0             27m   app.kubernetes.io/component=app,app.kubernetes.io/instance=banklab-kong,app.kubernetes.io/managed-by=Helm,app.kubernetes.io/name=gateway,app.kubernetes.io/version=3.9,app=banklab-kong-gateway,banklab.konghq.com/component=gateway,banklab.konghq.com/platform-layer=gateway,helm.sh/chart=gateway-3.2.0,pod-template-hash=75b48d447c,version=3.9

## Kong Services
NAME                                         TYPE           CLUSTER-IP     EXTERNAL-IP     PORT(S)               AGE
banklab-kong-controller-metrics              ClusterIP      10.233.2.43    <none>          10255/TCP,10254/TCP   27m
banklab-kong-controller-validation-webhook   ClusterIP      10.233.44.82   <none>          443/TCP               27m
banklab-kong-gateway-admin                   ClusterIP      None           <none>          8444/TCP              27m
banklab-kong-gateway-proxy                   LoadBalancer   10.233.33.79   192.168.20.22   80:30751/TCP          27m

## Kong Secret Names
NAME                                                    TYPE                DATA   AGE
banklab-kong-controller-validation-webhook-ca-keypair   kubernetes.io/tls   2      27m
banklab-kong-controller-validation-webhook-keypair      kubernetes.io/tls   2      27m

## GatewayClass
NAME   CONTROLLER                          ACCEPTED   AGE
kong   konghq.com/kic-gateway-controller   True       27m

## Gateways
NAME            CLASS   ADDRESS         PROGRAMMED   AGE
kong-external   kong    192.168.20.22   True         27m
kong-internal   kong    192.168.20.22   True         27m

## HTTPRoutes
NAME                  HOSTNAMES                              AGE
kong-smoke-external   ["kong-smoke.external.banklab.test"]   27m
kong-smoke-internal   ["kong-smoke.internal.banklab.test"]   27m

## GatewayClass Description
Name:         kong
Namespace:    
Labels:       banklab.konghq.com/managed-by=gitops
              banklab.konghq.com/owner=platform-team
              banklab.konghq.com/platform-layer=gateway
Annotations:  konghq.com/gatewayclass-unmanaged: true
API Version:  gateway.networking.k8s.io/v1
Kind:         GatewayClass
Metadata:
  Creation Timestamp:  2026-07-06T08:56:21Z
  Generation:          1
  Resource Version:    74622352
  UID:                 e729aa14-f287-449d-8edb-8ef340d21403
Spec:
  Controller Name:  konghq.com/kic-gateway-controller
Status:
  Conditions:
    Last Transition Time:  2026-07-06T09:10:12Z
    Message:               the gatewayclass has been accepted by the controller
    Observed Generation:   1
    Reason:                Accepted
    Status:                True
    Type:                  Accepted
Events:                    <none>

## Gateway Description
Name:         kong-external
Namespace:    platform-kong
Labels:       banklab.konghq.com/exposure=external
              banklab.konghq.com/managed-by=gitops
              banklab.konghq.com/owner=platform-team
              banklab.konghq.com/platform-layer=gateway
Annotations:  konghq.com/publish-service: platform-kong/banklab-kong-gateway-proxy
API Version:  gateway.networking.k8s.io/v1
Kind:         Gateway
Metadata:
  Creation Timestamp:  2026-07-06T08:56:21Z
  Generation:          1
  Resource Version:    74622361
  UID:                 a39653b9-a1c7-4449-85f5-aa8bb876562d
Spec:
  Gateway Class Name:  kong
  Listeners:
    Allowed Routes:
      Namespaces:
        From:  All
    Hostname:  *.external.banklab.test
    Name:      http
    Port:      80
    Protocol:  HTTP
Status:
  Addresses:
    Type:   IPAddress
    Value:  192.168.20.22
  Conditions:
    Last Transition Time:  2026-07-06T09:10:12Z
    Message:               this unmanaged gateway has been picked up by the controller and will be processed
    Observed Generation:   1
    Reason:                Accepted
    Status:                True
    Type:                  Accepted
    Last Transition Time:  2026-07-06T09:10:12Z
    Message:               
    Observed Generation:   1
    Reason:                Programmed
    Status:                True
    Type:                  Programmed
  Listeners:
    Attached Routes:  1
    Conditions:
      Last Transition Time:  2026-07-06T09:10:12Z
      Message:               
      Observed Generation:   1
      Reason:                Accepted
      Status:                True
      Type:                  Accepted
      Last Transition Time:  2026-07-06T09:10:12Z
      Message:               
      Observed Generation:   1
      Reason:                NoConflicts
      Status:                False
      Type:                  Conflicted
      Last Transition Time:  2026-07-06T09:10:12Z
      Message:               
      Observed Generation:   1
      Reason:                Programmed
      Status:                True
      Type:                  Programmed
      Last Transition Time:  2026-07-06T09:10:12Z
      Message:               
      Observed Generation:   1
      Reason:                ResolvedRefs
      Status:                True
      Type:                  ResolvedRefs
    Name:                    http
    Supported Kinds:
      Group:  gateway.networking.k8s.io
      Kind:   HTTPRoute
      Group:  gateway.networking.k8s.io
      Kind:   GRPCRoute
Events:       <none>


Name:         kong-internal
Namespace:    platform-kong
Labels:       banklab.konghq.com/exposure=internal
              banklab.konghq.com/managed-by=gitops
              banklab.konghq.com/owner=platform-team
              banklab.konghq.com/platform-layer=gateway
Annotations:  konghq.com/publish-service: platform-kong/banklab-kong-gateway-proxy
API Version:  gateway.networking.k8s.io/v1
Kind:         Gateway
Metadata:
  Creation Timestamp:  2026-07-06T08:56:21Z
  Generation:          1
  Resource Version:    74622363
  UID:                 8b3b19f9-ed73-4518-9d9b-a68f2bcdda09
Spec:
  Gateway Class Name:  kong
  Listeners:
    Allowed Routes:
      Namespaces:
        From:  All
    Hostname:  *.internal.banklab.test
    Name:      http
    Port:      80
    Protocol:  HTTP
Status:
  Addresses:
    Type:   IPAddress
    Value:  192.168.20.22
  Conditions:
    Last Transition Time:  2026-07-06T09:10:12Z
    Message:               this unmanaged gateway has been picked up by the controller and will be processed
    Observed Generation:   1
    Reason:                Accepted
    Status:                True
    Type:                  Accepted
    Last Transition Time:  2026-07-06T09:10:12Z
    Message:               
    Observed Generation:   1
    Reason:                Programmed
    Status:                True
    Type:                  Programmed
  Listeners:
    Attached Routes:  1
    Conditions:
      Last Transition Time:  2026-07-06T09:10:13Z
      Message:               
      Observed Generation:   1
      Reason:                Accepted
      Status:                True
      Type:                  Accepted
      Last Transition Time:  2026-07-06T09:10:13Z
      Message:               
      Observed Generation:   1
      Reason:                NoConflicts
      Status:                False
      Type:                  Conflicted
      Last Transition Time:  2026-07-06T09:10:13Z
      Message:               
      Observed Generation:   1
      Reason:                Programmed
      Status:                True
      Type:                  Programmed
      Last Transition Time:  2026-07-06T09:10:13Z
      Message:               
      Observed Generation:   1
      Reason:                ResolvedRefs
      Status:                True
      Type:                  ResolvedRefs
    Name:                    http
    Supported Kinds:
      Group:  gateway.networking.k8s.io
      Kind:   HTTPRoute
      Group:  gateway.networking.k8s.io
      Kind:   GRPCRoute
Events:       <none>

## HTTPRoute Description
Name:         kong-smoke-external
Namespace:    platform-kong-smoke
Labels:       banklab.konghq.com/not-business-api=true
              banklab.konghq.com/platform-layer=gateway
Annotations:  <none>
API Version:  gateway.networking.k8s.io/v1
Kind:         HTTPRoute
Metadata:
  Creation Timestamp:  2026-07-06T08:56:21Z
  Generation:          1
  Resource Version:    74622403
  UID:                 df5402f1-2dfa-4ac7-96af-3306b242345d
Spec:
  Hostnames:
    kong-smoke.external.banklab.test
  Parent Refs:
    Group:         gateway.networking.k8s.io
    Kind:          Gateway
    Name:          kong-external
    Namespace:     platform-kong
    Section Name:  http
  Rules:
    Backend Refs:
      Group:   
      Kind:    Service
      Name:    banklab-kong-smoke
      Port:    80
      Weight:  1
    Matches:
      Path:
        Type:   PathPrefix
        Value:  /
Status:
  Parents:
    Conditions:
      Last Transition Time:  2026-07-06T09:10:12Z
      Message:               
      Observed Generation:   1
      Reason:                Accepted
      Status:                True
      Type:                  Accepted
      Last Transition Time:  2026-07-06T09:10:12Z
      Message:               
      Observed Generation:   1
      Reason:                ResolvedRefs
      Status:                True
      Type:                  ResolvedRefs
      Last Transition Time:  2026-07-06T09:10:18Z
      Message:               
      Observed Generation:   1
      Reason:                ConfiguredInGateway
      Status:                True
      Type:                  Programmed
    Controller Name:         konghq.com/kic-gateway-controller
    Parent Ref:
      Group:         gateway.networking.k8s.io
      Kind:          Gateway
      Name:          kong-external
      Namespace:     platform-kong
      Section Name:  http
Events:              <none>


Name:         kong-smoke-internal
Namespace:    platform-kong-smoke
Labels:       banklab.konghq.com/not-business-api=true
              banklab.konghq.com/platform-layer=gateway
Annotations:  <none>
API Version:  gateway.networking.k8s.io/v1
Kind:         HTTPRoute
Metadata:
  Creation Timestamp:  2026-07-06T08:56:21Z
  Generation:          1
  Resource Version:    74622404
  UID:                 e43d6354-3ca5-414e-a434-1d9deb24cd7a
Spec:
  Hostnames:
    kong-smoke.internal.banklab.test
  Parent Refs:
    Group:         gateway.networking.k8s.io
    Kind:          Gateway
    Name:          kong-internal
    Namespace:     platform-kong
    Section Name:  http
  Rules:
    Backend Refs:
      Group:   
      Kind:    Service
      Name:    banklab-kong-smoke
      Port:    80
      Weight:  1
    Matches:
      Path:
        Type:   PathPrefix
        Value:  /
Status:
  Parents:
    Conditions:
      Last Transition Time:  2026-07-06T09:10:12Z
      Message:               
      Observed Generation:   1
      Reason:                Accepted
      Status:                True
      Type:                  Accepted
      Last Transition Time:  2026-07-06T09:10:12Z
      Message:               
      Observed Generation:   1
      Reason:                ResolvedRefs
      Status:                True
      Type:                  ResolvedRefs
      Last Transition Time:  2026-07-06T09:10:18Z
      Message:               
      Observed Generation:   1
      Reason:                ConfiguredInGateway
      Status:                True
      Type:                  Programmed
    Controller Name:         konghq.com/kic-gateway-controller
    Parent Ref:
      Group:         gateway.networking.k8s.io
      Kind:          Gateway
      Name:          kong-internal
      Namespace:     platform-kong
      Section Name:  http
Events:              <none>

## KIC Logs
2026-07-06T09:17:30Z	info	controllers.Gateway	Gateway provisioning complete	{"GatewayV1Gateway": {"name":"kong-external","namespace":"platform-kong"}, "v": 0, "namespace": "platform-kong", "name": "kong-external"}
2026-07-06T09:17:30Z	info	controllers.Gateway	Gateway provisioning complete	{"GatewayV1Gateway": {"name":"kong-internal","namespace":"platform-kong"}, "v": 0, "namespace": "platform-kong", "name": "kong-internal"}
2026-07-06T09:17:37Z	info	Successfully synced configuration to Kong	{"url": "https://10.233.70.117:8444", "update_strategy": "InMemory", "v": 0, "duration": "117ms"}
2026-07-06T09:17:37Z	info	Successfully synced configuration to Kong	{"url": "https://10.233.65.112:8444", "update_strategy": "InMemory", "v": 0, "duration": "115ms"}
2026-07-06T09:17:37Z	info	controllers.HTTPRoute	HTTPRoute has been configured on the data-plane	{"GatewayV1HTTPRoute": {"name":"kong-smoke-external","namespace":"platform-kong-smoke"}, "v": 0, "namespace": "platform-kong-smoke", "name": "kong-smoke-external"}
2026-07-06T09:17:37Z	info	controllers.HTTPRoute	HTTPRoute has been configured on the data-plane	{"GatewayV1HTTPRoute": {"name":"kong-smoke-internal","namespace":"platform-kong-smoke"}, "v": 0, "namespace": "platform-kong-smoke", "name": "kong-smoke-internal"}
2026-07-06T09:17:39Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "IngressClassParameters.configuration.konghq.com", "error": "no matches for kind \"IngressClassParameters\" in version \"configuration.konghq.com/v1alpha1\""}
2026-07-06T09:17:39Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongPlugin.configuration.konghq.com", "error": "no matches for kind \"KongPlugin\" in version \"configuration.konghq.com/v1\""}
2026-07-06T09:17:39Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "TCPIngress.configuration.konghq.com", "error": "no matches for kind \"TCPIngress\" in version \"configuration.konghq.com/v1beta1\""}
2026-07-06T09:17:39Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "UDPIngress.configuration.konghq.com", "error": "no matches for kind \"UDPIngress\" in version \"configuration.konghq.com/v1beta1\""}
2026-07-06T09:17:39Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongIngress.configuration.konghq.com", "error": "no matches for kind \"KongIngress\" in version \"configuration.konghq.com/v1\""}
2026-07-06T09:17:39Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongCustomEntity.configuration.konghq.com", "error": "no matches for kind \"KongCustomEntity\" in version \"configuration.konghq.com/v1alpha1\""}
2026-07-06T09:17:39Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongClusterPlugin.configuration.konghq.com", "error": "no matches for kind \"KongClusterPlugin\" in version \"configuration.konghq.com/v1\""}
2026-07-06T09:17:39Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongConsumerGroup.configuration.konghq.com", "error": "no matches for kind \"KongConsumerGroup\" in version \"configuration.konghq.com/v1beta1\""}
2026-07-06T09:17:39Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongUpstreamPolicy.configuration.konghq.com", "error": "no matches for kind \"KongUpstreamPolicy\" in version \"configuration.konghq.com/v1beta1\""}
2026-07-06T09:17:39Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongVault.configuration.konghq.com", "error": "no matches for kind \"KongVault\" in version \"configuration.konghq.com/v1alpha1\""}
2026-07-06T09:17:39Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongConsumer.configuration.konghq.com", "error": "no matches for kind \"KongConsumer\" in version \"configuration.konghq.com/v1\""}
2026-07-06T09:17:40Z	info	controllers.HTTPRoute	HTTPRoute has been configured on the data-plane	{"GatewayV1HTTPRoute": {"name":"kong-smoke-external","namespace":"platform-kong-smoke"}, "v": 0, "namespace": "platform-kong-smoke", "name": "kong-smoke-external"}
2026-07-06T09:17:40Z	info	controllers.HTTPRoute	HTTPRoute has been configured on the data-plane	{"GatewayV1HTTPRoute": {"name":"kong-smoke-internal","namespace":"platform-kong-smoke"}, "v": 0, "namespace": "platform-kong-smoke", "name": "kong-smoke-internal"}
time="2026-07-06T09:17:42Z" level=error msg="failed to forward report" error="failed to connect to reporting server: dial tcp: lookup kong-hf.konghq.com: i/o timeout" forwarder=TLSForwarder
2026-07-06T09:17:49Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "IngressClassParameters.configuration.konghq.com", "error": "no matches for kind \"IngressClassParameters\" in version \"configuration.konghq.com/v1alpha1\""}
2026-07-06T09:17:49Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongConsumer.configuration.konghq.com", "error": "no matches for kind \"KongConsumer\" in version \"configuration.konghq.com/v1\""}
2026-07-06T09:17:49Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongIngress.configuration.konghq.com", "error": "no matches for kind \"KongIngress\" in version \"configuration.konghq.com/v1\""}
2026-07-06T09:17:49Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "TCPIngress.configuration.konghq.com", "error": "no matches for kind \"TCPIngress\" in version \"configuration.konghq.com/v1beta1\""}
2026-07-06T09:17:49Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "UDPIngress.configuration.konghq.com", "error": "no matches for kind \"UDPIngress\" in version \"configuration.konghq.com/v1beta1\""}
2026-07-06T09:17:49Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongClusterPlugin.configuration.konghq.com", "error": "no matches for kind \"KongClusterPlugin\" in version \"configuration.konghq.com/v1\""}
2026-07-06T09:17:49Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongConsumerGroup.configuration.konghq.com", "error": "no matches for kind \"KongConsumerGroup\" in version \"configuration.konghq.com/v1beta1\""}
2026-07-06T09:17:49Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongVault.configuration.konghq.com", "error": "no matches for kind \"KongVault\" in version \"configuration.konghq.com/v1alpha1\""}
2026-07-06T09:17:49Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongPlugin.configuration.konghq.com", "error": "no matches for kind \"KongPlugin\" in version \"configuration.konghq.com/v1\""}
2026-07-06T09:17:49Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongUpstreamPolicy.configuration.konghq.com", "error": "no matches for kind \"KongUpstreamPolicy\" in version \"configuration.konghq.com/v1beta1\""}
2026-07-06T09:17:49Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongCustomEntity.configuration.konghq.com", "error": "no matches for kind \"KongCustomEntity\" in version \"configuration.konghq.com/v1alpha1\""}
2026-07-06T09:17:59Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "IngressClassParameters.configuration.konghq.com", "error": "no matches for kind \"IngressClassParameters\" in version \"configuration.konghq.com/v1alpha1\""}
2026-07-06T09:17:59Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "UDPIngress.configuration.konghq.com", "error": "no matches for kind \"UDPIngress\" in version \"configuration.konghq.com/v1beta1\""}
2026-07-06T09:17:59Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongClusterPlugin.configuration.konghq.com", "error": "no matches for kind \"KongClusterPlugin\" in version \"configuration.konghq.com/v1\""}
2026-07-06T09:17:59Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongIngress.configuration.konghq.com", "error": "no matches for kind \"KongIngress\" in version \"configuration.konghq.com/v1\""}
2026-07-06T09:17:59Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongConsumer.configuration.konghq.com", "error": "no matches for kind \"KongConsumer\" in version \"configuration.konghq.com/v1\""}
2026-07-06T09:17:59Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongCustomEntity.configuration.konghq.com", "error": "no matches for kind \"KongCustomEntity\" in version \"configuration.konghq.com/v1alpha1\""}
2026-07-06T09:17:59Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongPlugin.configuration.konghq.com", "error": "no matches for kind \"KongPlugin\" in version \"configuration.konghq.com/v1\""}
2026-07-06T09:17:59Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongConsumerGroup.configuration.konghq.com", "error": "no matches for kind \"KongConsumerGroup\" in version \"configuration.konghq.com/v1beta1\""}
2026-07-06T09:17:59Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "TCPIngress.configuration.konghq.com", "error": "no matches for kind \"TCPIngress\" in version \"configuration.konghq.com/v1beta1\""}
2026-07-06T09:17:59Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongUpstreamPolicy.configuration.konghq.com", "error": "no matches for kind \"KongUpstreamPolicy\" in version \"configuration.konghq.com/v1beta1\""}
2026-07-06T09:17:59Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongVault.configuration.konghq.com", "error": "no matches for kind \"KongVault\" in version \"configuration.konghq.com/v1alpha1\""}
2026-07-06T09:18:09Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "IngressClassParameters.configuration.konghq.com", "error": "no matches for kind \"IngressClassParameters\" in version \"configuration.konghq.com/v1alpha1\""}
2026-07-06T09:18:09Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongCustomEntity.configuration.konghq.com", "error": "no matches for kind \"KongCustomEntity\" in version \"configuration.konghq.com/v1alpha1\""}
2026-07-06T09:18:09Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongConsumer.configuration.konghq.com", "error": "no matches for kind \"KongConsumer\" in version \"configuration.konghq.com/v1\""}
2026-07-06T09:18:09Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongIngress.configuration.konghq.com", "error": "no matches for kind \"KongIngress\" in version \"configuration.konghq.com/v1\""}
2026-07-06T09:18:09Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongClusterPlugin.configuration.konghq.com", "error": "no matches for kind \"KongClusterPlugin\" in version \"configuration.konghq.com/v1\""}
2026-07-06T09:18:09Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "TCPIngress.configuration.konghq.com", "error": "no matches for kind \"TCPIngress\" in version \"configuration.konghq.com/v1beta1\""}
2026-07-06T09:18:09Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "UDPIngress.configuration.konghq.com", "error": "no matches for kind \"UDPIngress\" in version \"configuration.konghq.com/v1beta1\""}
2026-07-06T09:18:09Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongPlugin.configuration.konghq.com", "error": "no matches for kind \"KongPlugin\" in version \"configuration.konghq.com/v1\""}
2026-07-06T09:18:09Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongConsumerGroup.configuration.konghq.com", "error": "no matches for kind \"KongConsumerGroup\" in version \"configuration.konghq.com/v1beta1\""}
2026-07-06T09:18:09Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongUpstreamPolicy.configuration.konghq.com", "error": "no matches for kind \"KongUpstreamPolicy\" in version \"configuration.konghq.com/v1beta1\""}
2026-07-06T09:18:09Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongVault.configuration.konghq.com", "error": "no matches for kind \"KongVault\" in version \"configuration.konghq.com/v1alpha1\""}
2026-07-06T09:18:19Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "IngressClassParameters.configuration.konghq.com", "error": "no matches for kind \"IngressClassParameters\" in version \"configuration.konghq.com/v1alpha1\""}
2026-07-06T09:18:19Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongConsumerGroup.configuration.konghq.com", "error": "no matches for kind \"KongConsumerGroup\" in version \"configuration.konghq.com/v1beta1\""}
2026-07-06T09:18:19Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "TCPIngress.configuration.konghq.com", "error": "no matches for kind \"TCPIngress\" in version \"configuration.konghq.com/v1beta1\""}
2026-07-06T09:18:19Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "UDPIngress.configuration.konghq.com", "error": "no matches for kind \"UDPIngress\" in version \"configuration.konghq.com/v1beta1\""}
2026-07-06T09:18:19Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongIngress.configuration.konghq.com", "error": "no matches for kind \"KongIngress\" in version \"configuration.konghq.com/v1\""}
2026-07-06T09:18:19Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongCustomEntity.configuration.konghq.com", "error": "no matches for kind \"KongCustomEntity\" in version \"configuration.konghq.com/v1alpha1\""}
2026-07-06T09:18:19Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongPlugin.configuration.konghq.com", "error": "no matches for kind \"KongPlugin\" in version \"configuration.konghq.com/v1\""}
2026-07-06T09:18:19Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongClusterPlugin.configuration.konghq.com", "error": "no matches for kind \"KongClusterPlugin\" in version \"configuration.konghq.com/v1\""}
2026-07-06T09:18:19Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongVault.configuration.konghq.com", "error": "no matches for kind \"KongVault\" in version \"configuration.konghq.com/v1alpha1\""}
2026-07-06T09:18:19Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongUpstreamPolicy.configuration.konghq.com", "error": "no matches for kind \"KongUpstreamPolicy\" in version \"configuration.konghq.com/v1beta1\""}
2026-07-06T09:18:19Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongConsumer.configuration.konghq.com", "error": "no matches for kind \"KongConsumer\" in version \"configuration.konghq.com/v1\""}
2026-07-06T09:18:29Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "IngressClassParameters.configuration.konghq.com", "error": "no matches for kind \"IngressClassParameters\" in version \"configuration.konghq.com/v1alpha1\""}
2026-07-06T09:18:29Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongConsumer.configuration.konghq.com", "error": "no matches for kind \"KongConsumer\" in version \"configuration.konghq.com/v1\""}
2026-07-06T09:18:29Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongIngress.configuration.konghq.com", "error": "no matches for kind \"KongIngress\" in version \"configuration.konghq.com/v1\""}
2026-07-06T09:18:29Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "TCPIngress.configuration.konghq.com", "error": "no matches for kind \"TCPIngress\" in version \"configuration.konghq.com/v1beta1\""}
2026-07-06T09:18:29Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "UDPIngress.configuration.konghq.com", "error": "no matches for kind \"UDPIngress\" in version \"configuration.konghq.com/v1beta1\""}
2026-07-06T09:18:29Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongUpstreamPolicy.configuration.konghq.com", "error": "no matches for kind \"KongUpstreamPolicy\" in version \"configuration.konghq.com/v1beta1\""}
2026-07-06T09:18:29Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongConsumerGroup.configuration.konghq.com", "error": "no matches for kind \"KongConsumerGroup\" in version \"configuration.konghq.com/v1beta1\""}
2026-07-06T09:18:29Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongPlugin.configuration.konghq.com", "error": "no matches for kind \"KongPlugin\" in version \"configuration.konghq.com/v1\""}
2026-07-06T09:18:29Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongVault.configuration.konghq.com", "error": "no matches for kind \"KongVault\" in version \"configuration.konghq.com/v1alpha1\""}
2026-07-06T09:18:29Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongCustomEntity.configuration.konghq.com", "error": "no matches for kind \"KongCustomEntity\" in version \"configuration.konghq.com/v1alpha1\""}
2026-07-06T09:18:29Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongClusterPlugin.configuration.konghq.com", "error": "no matches for kind \"KongClusterPlugin\" in version \"configuration.konghq.com/v1\""}
2026-07-06T09:18:39Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "IngressClassParameters.configuration.konghq.com", "error": "no matches for kind \"IngressClassParameters\" in version \"configuration.konghq.com/v1alpha1\""}
2026-07-06T09:18:39Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongConsumer.configuration.konghq.com", "error": "no matches for kind \"KongConsumer\" in version \"configuration.konghq.com/v1\""}
2026-07-06T09:18:39Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "UDPIngress.configuration.konghq.com", "error": "no matches for kind \"UDPIngress\" in version \"configuration.konghq.com/v1beta1\""}
2026-07-06T09:18:39Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "TCPIngress.configuration.konghq.com", "error": "no matches for kind \"TCPIngress\" in version \"configuration.konghq.com/v1beta1\""}
2026-07-06T09:18:39Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongIngress.configuration.konghq.com", "error": "no matches for kind \"KongIngress\" in version \"configuration.konghq.com/v1\""}
2026-07-06T09:18:39Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongPlugin.configuration.konghq.com", "error": "no matches for kind \"KongPlugin\" in version \"configuration.konghq.com/v1\""}
2026-07-06T09:18:39Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongConsumerGroup.configuration.konghq.com", "error": "no matches for kind \"KongConsumerGroup\" in version \"configuration.konghq.com/v1beta1\""}
2026-07-06T09:18:39Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongClusterPlugin.configuration.konghq.com", "error": "no matches for kind \"KongClusterPlugin\" in version \"configuration.konghq.com/v1\""}
2026-07-06T09:18:39Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongUpstreamPolicy.configuration.konghq.com", "error": "no matches for kind \"KongUpstreamPolicy\" in version \"configuration.konghq.com/v1beta1\""}
2026-07-06T09:18:39Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongCustomEntity.configuration.konghq.com", "error": "no matches for kind \"KongCustomEntity\" in version \"configuration.konghq.com/v1alpha1\""}
2026-07-06T09:18:39Z	error	controller-runtime.source.Kind	if kind is a CRD, it should be installed before calling Start	{"kind": "KongVault.configuration.konghq.com", "error": "no matches for kind \"KongVault\" in version \"configuration.konghq.com/v1alpha1\""}
2026-07-06T09:18:40Z	info	controllers.Dynamic/KongLicense	All required CustomResourceDefinitions are installed, setting up the controller	{"CustomResourceDefinition": {"name":"konglicenses.configuration.konghq.com"}, "v": 0}
2026-07-06T09:18:40Z	info	controllers.KongLicense	Starting EventSource	{"source": "channel source: 0xc0002f9110", "v": 0}
2026-07-06T09:18:40Z	info	controllers.KongLicense	Starting EventSource	{"source": "kind source: *v1alpha1.KongLicense", "v": 0}
2026-07-06T09:18:41Z	info	controllers.KongLicense	Starting Controller	{"v": 0}
2026-07-06T09:18:41Z	info	controllers.KongLicense	Starting workers	{"v": 0, "worker count": 1}
2026-07-06T09:18:43Z	info	controller-runtime.certwatcher	Updated current TLS certificate	{"v": 0}
2026-07-06T09:18:49Z	info	controller-runtime.cache	Warning: configuration.konghq.com/v1beta1 TCPIngress is deprecated	{"v": 0}
2026-07-06T09:18:49Z	info	controller-runtime.cache	Warning: configuration.konghq.com/v1beta1 TCPIngress is deprecated	{"v": 0}
2026-07-06T09:18:49Z	info	controller-runtime.cache	Warning: configuration.konghq.com/v1beta1 UDPIngress is deprecated	{"v": 0}
2026-07-06T09:18:49Z	info	controller-runtime.cache	Warning: configuration.konghq.com/v1beta1 UDPIngress is deprecated	{"v": 0}
2026-07-06T09:18:49Z	info	controller-runtime.cache	Warning: configuration.konghq.com/v1 KongIngress is deprecated	{"v": 0}
2026-07-06T09:18:49Z	info	controller-runtime.cache	Warning: configuration.konghq.com/v1 KongIngress is deprecated	{"v": 0}
2026-07-06T09:18:49Z	info	controllers.IngressClassParameters	Starting Controller	{"v": 0}
2026-07-06T09:18:49Z	info	controllers.IngressClassParameters	Starting workers	{"v": 0, "worker count": 1}
2026-07-06T09:18:49Z	info	controllers.TCPIngress	Starting Controller	{"v": 0}
2026-07-06T09:18:49Z	info	controllers.TCPIngress	Starting workers	{"v": 0, "worker count": 1}
2026-07-06T09:18:49Z	info	controllers.KongPlugin	Starting Controller	{"v": 0}
2026-07-06T09:18:49Z	info	controllers.KongPlugin	Starting workers	{"v": 0, "worker count": 1}
2026-07-06T09:18:49Z	info	controllers.KongConsumerGroup	Starting Controller	{"v": 0}
2026-07-06T09:18:49Z	info	controllers.KongUpstreamPolicy	Starting Controller	{"v": 0}
2026-07-06T09:18:49Z	info	controllers.KongUpstreamPolicy	Starting workers	{"v": 0, "worker count": 1}
2026-07-06T09:18:49Z	info	controllers.KongConsumer	Starting Controller	{"v": 0}
2026-07-06T09:18:49Z	info	controllers.KongConsumer	Starting workers	{"v": 0, "worker count": 1}
2026-07-06T09:18:49Z	info	controllers.KongClusterPlugin	Starting Controller	{"v": 0}
2026-07-06T09:18:49Z	info	controllers.KongCustomEntity	Starting Controller	{"v": 0}
2026-07-06T09:18:49Z	info	controllers.KongClusterPlugin	Starting workers	{"v": 0, "worker count": 1}
2026-07-06T09:18:49Z	info	controllers.UDPIngress	Starting Controller	{"v": 0}
2026-07-06T09:18:49Z	info	controllers.KongVault	Starting Controller	{"v": 0}
2026-07-06T09:18:49Z	info	controllers.KongConsumerGroup	Starting workers	{"v": 0, "worker count": 1}
2026-07-06T09:18:49Z	info	controllers.KongVault	Starting workers	{"v": 0, "worker count": 1}
2026-07-06T09:18:49Z	info	controllers.KongCustomEntity	Starting workers	{"v": 0, "worker count": 1}
2026-07-06T09:18:49Z	info	controllers.KongIngress	Starting Controller	{"v": 0}
2026-07-06T09:18:49Z	info	controllers.KongIngress	Starting workers	{"v": 0, "worker count": 1}
2026-07-06T09:18:49Z	info	controllers.UDPIngress	Starting workers	{"v": 0, "worker count": 1}
