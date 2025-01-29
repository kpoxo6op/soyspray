# Private kubernetes ingress with tailscale operator, cert-manager and external-dns | by Mattia Forcellese | Medium

![Mattia
Forcellese](https://miro.medium.com/v2/resize:fill:88:88/1*Ox7IKl1SRz5EsfAOsry7Tw.png)
[Mattia Forcellese](https://medium.com/@mattiaforc)

In this article you will learn how to expose an ingress privately on a tailnet
that is accessible only via Tailscale, with a custom domain, automatic DNS
records and valid Let’s Encrypt certificates.
If you don’t need a custom domain to expose ingresses and you are ok using the
default Tailscale [MagicDNS](https://tailscale.com/kb/1081/magicdns), you can
skip some of the following steps because you won’t need external-dns and
cert-manager.

What do we want to achieve? We want to be able to access some service on
kubernetes only from devices connected to tailscale. Suppose we have the domain
`foo.com`, we want to configure an ingress for Grafana that responds to
`grafana.foo.com` .

```

**Requirements**:

* A [tailscale account](https://login.tailscale.com/start): I am using a free
    plan, so any other plan works as well.
* A kubernetes cluster: I am running a cloud managed kubernetes, hosted on
    Aruba Cloud (based in Italy), but you can also run it locally with
    minikube/kind or any other kubernetes distribution.
* A registered domain: in this example I am using a domain on Cloudflare, and
    I will be using external-dns with Cloudflare, but any of the [supported
    providers](https://github.com/kubernetes-sigs/external-dns?tab=readme-ov-file)
    should be fine as well.

Let’s deploy what we need
-------------------------

> Note that we are doing lots of manual installation with helm and the kubectl
> CLI; it would be wiser to use a CD tool like Argo CD or Flux CD and keep
> manifests/values versioned in a Git repository.

First, we are going to install the tailscale operator. The [official
docs](https://tailscale.com/kb/1236/kubernetes-operator#setting-up-the-kubernetes-operator)
for deploying the operator are very thorough and accurate, so I suggest you
follow that to be sure you use the most up-to-date version. You can install it
via helm and there are no values to set other than the OAuth credentials that
tailscale requires you to setup. An example `values.yaml` file could look this:

```
oauth:
  clientId: xxxx
  clientSecret: xxxx
```

Second, we are going to deploy cert-manager; again this is pretty
straightforward if you look at [their
documentation](https://cert-manager.io/docs/installation/), you can deploy it
via Helm with no particular configuration or via static manifests. This is
optional if you plan to use the default Tailscale MagicDNS.

Next comes external-dns: in this case the configuration pretty much depends on
your DNS provider; there are [many to choose
from](https://github.com/kubernetes-sigs/external-dns?tab=readme-ov-file#deploying-to-a-cluster),
follow the configuration steps according. For Cloudflare, an example
`values.yaml` file would be like this:

```
provider:
  name: cloudflare
env:
  - name: CF_API_TOKEN
    value: xxxx
serviceMonitor:
  enabled: true
txtOwnerId: <a static ID that identifies this k8s cluster>
domainFilters:
  - domain.com
policy: sync # Important to note that if not set to sync (by default is write-only), DNS records wont't be deleted when we delete ingress resources
```

Lastly, we need to install and expose the ingress controller only on the
Tailscale private network. That’s where the interesting part begins, but before
that let’s take a small step back and talk about the Tailscale operator and how
it works for services and ingresses.

Tailscale operator
------------------

The tailscale operator can expose workloads to the tailnet in three different
ways:

* Create a `LoadBalancer` type `Service` with the `tailscale`
    `[loadBalancerClass](https://tailscale.com/kb/1236/kubernetes-operator#loadbalancerclass)`
    that fronts your workload.
* [Annotate](https://tailscale.com/kb/1236/kubernetes-operator#annotations) an
    existing `Service` that fronts your workload
* Create an
    `[Ingress](https://tailscale.com/kb/1236/kubernetes-operator#ingress-resource)`
    [resource](https://tailscale.com/kb/1236/kubernetes-operator#ingress-resource)
    fronting a `Service` or `Service`s for the workloads you wish to expose.

I want to focus mainly on the first and the third option. If you create an
ingress resource with the `tailscale` ingress class, you will automatically get
a tailnet IP, like _100.xxx.xxx.xxx_, and a MagicDNS record, if enabled, that
you can call when you are connected to tailnet. The FQDN for ingress will be
like this: `grafana.tailxxxx.ts.net.`This would the easiest option; you
simply need to enable HTTPS on tailscale and all traffic will be encrypted via
Let’s Encrypt certificates that are handled directly by Tailscale. There are a
few limitations though: you can only use the tailxxxx.ts.net domain, so it’s
harder to remember and if used for internal services by a company, it’s probably
an unwanted result. Another downside is that you can’t use all the regular
features of your ingress controller (in this example I am using Nginx but any
other ingress controller is also fine) because traffic is handled directly by a
Tailscale pod that serves that specific ingress.
If you are fine with the limitations above, than you are already good to go: if
you deployed everything from the previous steps, you can create an ingress with
`tailscale` class and you should see the newly added ingress in the tailscale
`Machines` in the Tailscale control panel, and be able to reach it via its FQDN
or IP.

This brings us to the first way of exposing workloads to tailnet, which is
creating `LoadBalancer` `Service`s that get automatically assigned an IP inside
the tailnet, just as a normal `LoadBalancer` would assign the service an IP in a
managed Kubernetes clusters (AKS, EKS, etc…). That’s exactly what we want to do
to expose the ingress controller: so that we only have one service exposed in
the tailnet that will respond to various ingresses (this is the normal ingress
controller scenario). Remember that we want to be able to call our services via
the URL `grafana.foo.com` , so we also need to configure DNS records that point
to the tailscale private IP for the ingress controller.

Back to the ingress controller
------------------------------

Now that we know how to expose the ingress controller, we can deploy it (or
simply reconfigure the service) with a `tailscale` `LoadBalancer` . Let’s deploy
[nginx ingress](https://github.com/kubernetes/ingress-nginx) with the following
`values.yaml` file:

```
controller:
  config:
    ssl-redirect: "true"
    force-ssl-redirect: "true"
  replicaCount: 1
  service:
    type: LoadBalancer
    loadBalancerClass: tailscale
  ingressClassResource:
    default: false
  watchIngressWithoutClass: false
  metrics:
    enabled: true
    serviceMonitor:
      enabled: true
```

The `ssl-redirect` is enabled because I want to force services to work only via
HTTPS. Note that we don’t need to specify a default TLS certificate because we
will be using cert-manager to generate certificates on demand for every ingress.
You should see the deployment up and running, with 1 pod ready, and a `Service`
like this:

```
NAME                                 TYPE           CLUSTER-IP       EXTERNAL-IP                                                       PORT(S)                      AGE
ingress-nginx-controller             LoadBalancer   10.109.177.63    100.xxx.xxx.xxx,ingress-ingress-nginx-controller.tailxxxx.ts.net   80:31164/TCP,443:31468/TCP   21h
```

After deploying the nginx ingress, [we can configure a Let’s Encrypt
Issuer](https://cert-manager.io/docs/tutorials/acme/nginx-ingress/#step-6---configure-a-lets-encrypt-issuer)
(you could also start with the staging environment, because production has
strict rate limits):

```
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    email: "<email>"
    server: https://acme-v02.api.letsencrypt.org/directory
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
      - dns01:
          cloudflare:
            apiTokenSecretRef:
              name: cloudflare-api-token-secret
              key: api-token
```

The most important thing to note is that we are using the dns01 challenge
solver, since the ingress won’t be exposed publicly on the internet it would be
impossible to use a normal HTTP challenge. Please refer to the [exhaustive
cert-manager documentation about dns01
challenge](https://cert-manager.io/docs/configuration/acme/dns01/) and all the
DNS providers that can be used. In this case, I am using Cloudflare because the
example domain `foo.bar` I am using is registered with Cloudflare.

Configure an ingress
--------------------

Now that we have everything in place we can test the whole architecture, so we
are going to create an ingress for whatever application we want to expose. If
you have no application and want to try it out, I suggest you install the
[_classic_ podinfo application](https://github.com/stefanprodan/podinfo).
You need to define the ingress with a few annotations, to let external-dns and
cert-manager do their jobs:

```
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod # name of the issuer we defined before
    external-dns.alpha.kubernetes.io/hostname: grafana.foo.com
    kubernetes.io/tls-acme: "true"
  name: prometheus-kps-grafana
  namespace: prometheus
spec:
  ingressClassName: nginx
  rules:
  - host: grafana.foo.com
    http:
      paths:
      - backend:
          service:
            name: prometheus-kps-grafana
            port:
              number: 80
        path: /
        pathType: Prefix
  tls:
  - secretName: grafana.foo.com
    hosts:
    - grafana.foo.com
```

Once you create the ingress, the following will happen:

* cert-manager will generate the requested certificate for `grafana.foo.com`.
    You can check this simply by looking at the secrets in the same namespace of
    the ingress: you should see a secret named `grafana.foo.com`.
* Tailscale operator will expose the new ingress on the tailnet (via the IP of
    the nginx ingress controller that we deployed before). Again, you should see
    this in the `Machines` section of the Tailscale control panel.
* External-dns will publish a DNS A record for `grafana.foo.com` pointing to
    the tailnet IP (100.xxx.xxx.xxx)

You can now try to connect to Tailscale with any registered device (you can
[download the client here](https://tailscale.com/download)), and cURL the
ingress:

```
curl -v https://grafana.foo.com
*   Trying 100.xxx.xxx.xxx:443...
* Connected to grafana.foo.com (100.xxx.xxx.xxx) port 443 (#0)
* ALPN, offering h2
* ALPN, offering http/1.1
*  CAfile: /etc/ssl/certs/ca-certificates.crt
*  CApath: /etc/ssl/certs
* TLSv1.0 (OUT), TLS header, Certificate Status (22):
* TLSv1.3 (OUT), TLS handshake, Client hello (1):
* TLSv1.2 (IN), TLS header, Certificate Status (22):
* TLSv1.3 (IN), TLS handshake, Server hello (2):
* TLSv1.2 (IN), TLS header, Finished (20):
* TLSv1.2 (IN), TLS header, Supplemental data (23):
* TLSv1.3 (IN), TLS handshake, Encrypted Extensions (8):
* TLSv1.2 (IN), TLS header, Supplemental data (23):
* TLSv1.3 (IN), TLS handshake, Certificate (11):
* TLSv1.2 (IN), TLS header, Supplemental data (23):
* TLSv1.3 (IN), TLS handshake, CERT verify (15):
* TLSv1.2 (IN), TLS header, Supplemental data (23):
* TLSv1.3 (IN), TLS handshake, Finished (20):
* TLSv1.2 (OUT), TLS header, Finished (20):
* TLSv1.3 (OUT), TLS change cipher, Change cipher spec (1):
* TLSv1.2 (OUT), TLS header, Supplemental data (23):
* TLSv1.3 (OUT), TLS handshake, Finished (20):
* SSL connection using TLSv1.3 / TLS_AES_256_GCM_SHA384
* ALPN, server accepted to use h2
* Server certificate:
*  subject: CN=grafana.foo.com
*  start date: Jun 22 13:47:21 2024 GMT
*  expire date: Sep 20 13:47:20 2024 GMT
*  subjectAltName: host "grafana.foo.com" matched cert's "grafana.foo.com"
*  issuer: C=US; O=Let's Encrypt; CN=R10
*  SSL certificate verify ok.
...
* Connection #0 to host grafana.foo.com left intact
```

Final thoughts
--------------

We exposed a private ingress on the tailnet, on a custom domain `foo.bar` with
Let’s Encrypt valid certificates and a zero-trust posture. The configuration is
all automatic due to the integration with external-dns and cert-manager, so it’s
a really easy and rapid solution for enabling access to private ingresses in
kubernetes clusters (wherever they are located, whether on prem or on cloud)
only to authorized devices via Tailscale.

I’d really like to hear your thoughts and experiences on zero-trust
architectures in Kubernetes, VPNs and networking related stuff, especially in
small to medium startups; feel free to reach out to me via email or by
commenting this article if you want to have a chat on this topic or others :)

Thanks so much for reading, you can follow me here on Medium, on
[Linkedin](http://www.linkedin.com/in/mattia-forcellese-353887144) or
[Github](https://github.com/mattiaforc) for more! See you next time!
