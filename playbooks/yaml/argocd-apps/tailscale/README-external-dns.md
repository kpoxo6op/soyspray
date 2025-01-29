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


## o1 reply

Below is a conceptual “recipe” that pulls from Mattia’s article and from typical local/home-lab Kubernetes setups (with MetalLB, Ingress-NGINX, etc.) to help you get a stable Tailscale IP and avoid having to constantly update DNS entries or NextDNS rewrites. The gist is to let Tailscale Operator + external-dns handle the Tailscale IP automatically, so that Cloudflare DNS entries follow any changes if they do happen. You end up with a configuration where:

    Your Ingress Controller is published to Tailscale as a “LoadBalancer Service.”
    Tailscale Operator allocates (and tries to keep) a stable Tailscale IP for that Service.
    external-dns automatically publishes that IP to your domain on Cloudflare.
    cert-manager issues certificates via DNS-01 challenge, so you get valid TLS even though the IP is private and not publicly routable.

Because external-dns is also “watching” your Kubernetes resources, if the Tailscale IP does change (e.g., if you delete the Service and re-create it, or the Tailscale Operator decides it must move the IP), external-dns will automatically update Cloudflare’s A record in the background—no manual rewriting or fiddling with NextDNS.

Below is the overall process in more detail.
1. Install Tailscale Operator

Follow Tailscale Operator’s official docs/Helm chart. The main setting you need is the OAuth client credentials. You’ll end up with something like:

oauth:
  clientId: <TAILSCALE_OAUTH_CLIENT_ID>
  clientSecret: <TAILSCALE_OAUTH_CLIENT_SECRET>

Deploy that into your cluster. (You may also need to set appropriate RBAC if you have a locked-down cluster.)
2. Install external-dns (pointing to Cloudflare)

You’ll want external-dns to manage your *.soyspray.vip DNS records. A sample values.yaml for Helm might look like:

provider:
  name: cloudflare
env:
  - name: CF_API_TOKEN
    value: <YOUR_CLOUDFLARE_API_TOKEN>
domainFilters:
  - soyspray.vip
txtOwnerId: local-k8s-cluster
policy: sync   # ensures DNS records get deleted if you remove an Ingress

Make sure you have granted that Cloudflare token the correct permissions.

Installing external-dns:

helm repo add external-dns https://kubernetes-sigs.github.io/external-dns/
helm install external-dns external-dns/external-dns -f values.yaml

3. Install cert-manager (for Let’s Encrypt via DNS-01 challenge)

Cert-manager can be installed via Helm or static manifests. After that, define a ClusterIssuer that uses DNS-01 with Cloudflare:

apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: "your.email@example.com"
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
      - dns01:
          cloudflare:
            apiTokenSecretRef:
              name: cloudflare-api-token
              key: api-token

You’ll need a Secret named cloudflare-api-token containing the api-token key. Same Cloudflare token used in external-dns can be reused if permissions match.
4. Deploy the Ingress Controller as a Tailscale LoadBalancer

Now comes the important part: we want to “pin” the Ingress Controller behind a single Tailscale IP that rarely changes. By default, Tailscale Operator’s LoadBalancerClass tries to keep the assigned IP stable as long as you don’t delete and recreate that Service object. If you are in “day-to-day” usage and just re-deploy the Helm chart (without removing the Service), that Tailscale IP is likely to remain the same.
Example Helm values.yaml for NGINX Ingress

controller:
  ingressClassResource:
    name: nginx
    default: false
  watchIngressWithoutClass: false

  service:
    type: LoadBalancer
    # This is the key so Tailscale Operator picks it up
    loadBalancerClass: tailscale

  # Force HTTPS
  config:
    ssl-redirect: "true"
    force-ssl-redirect: "true"

  replicaCount: 1

Then install (or upgrade) the official NGINX Ingress chart:

helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm install ingress-nginx ingress-nginx/ingress-nginx -f values.yaml

Once it’s up, you should see a Service of type LoadBalancer with a Tailscale IP, for example:

NAME                      TYPE           CLUSTER-IP      EXTERNAL-IP                            PORT(S)                      AGE
ingress-nginx-controller  LoadBalancer  10.109.177.63   100.x.y.z,ingress-nginx.tailXXXX.ts.net 80:31164/TCP,443:31468/TCP   10m

5. Create the Ingress for your workload

Finally, you create an Ingress in your cluster referencing your real domain, soyspray.vip, plus the usual external-dns and cert-manager annotations:

apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: myapp-ingress
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    external-dns.alpha.kubernetes.io/hostname: "myapp.soyspray.vip"
    kubernetes.io/tls-acme: "true"
spec:
  ingressClassName: nginx
  rules:
    - host: myapp.soyspray.vip
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: myapp-svc
                port:
                  number: 80
  tls:
    - hosts:
        - myapp.soyspray.vip
      secretName: myapp-sso-tls

    The external-dns.alpha.kubernetes.io/hostname annotation instructs external-dns to create a DNS A record (myapp.soyspray.vip) in Cloudflare, pointing to the Tailscale IP assigned to the NGINX Ingress.
    cert-manager.io/cluster-issuer: "letsencrypt-prod" plus kubernetes.io/tls-acme: "true" ensures that cert-manager automatically generates a valid Let’s Encrypt certificate using DNS-01.

Result:

    Tailscale Operator sees that your ingress controller is a Tailscale LB and ensures the cluster has a stable 100.x.y.z IP.
    external-dns sees an Ingress with external-dns.alpha.kubernetes.io/hostname: "myapp.soyspray.vip", so it creates an A record in Cloudflare → 100.x.y.z.
    cert-manager fetches a Let’s Encrypt certificate for myapp.soyspray.vip, storing it in the Secret myapp-sso-tls. NGINX Ingress uses that for TLS.
    You connect from your phone’s Tailscale client. The domain myapp.soyspray.vip resolves to 100.x.y.z, your cluster is only accessible to Tailscale peers, and the certificate is fully valid.

6. What if the Tailscale IP changes anyway?

    In general, if you simply “helm upgrade” or “kubectl apply -f …” on the same Service, Tailscale Operator tries to preserve the same IP.
    If you delete and recreate the Service (or blow away the entire Tailscale operator instance), then you may get a new IP.
    But with external-dns, your DNS record will be automatically updated with that new IP. You do not need to manually track or reconfigure NextDNS rewrites.

Hence, the entire process becomes:

    Stable in everyday use (the IP usually stays the same).
    Self-healing if the IP does change: external-dns updates the Cloudflare record.
    Hands-off for certificate generation (cert-manager does it).

7. What if you want to keep NextDNS in the mix?

You mentioned using a NextDNS rewrite rule previously. If you prefer that approach to global DNS updates in Cloudflare, you can do something similar:

    Instead of letting external-dns manage Cloudflare’s public DNS, you could point NextDNS rewrite to the Tailscale IP.
    The big advantage of using external-dns & Cloudflare, though, is that if your Tailscale IP changes, that update is fully automated. If you rely on NextDNS rewrite alone, you have to update it manually.

Therefore, the easiest path to “no more rewriting” is to let external-dns manage the domain in Cloudflare so that myapp.soyspray.vip will always point to your Tailscale IP—no matter what.
8. Summary: The “Zero (Manual) Touch” Approach

The solution in Mattia’s article is exactly the same pattern you can use in a local cluster:

    Local cluster with MetalLB + NGINX Ingress.
    Tailscale Operator as a “LoadBalancer Class.”
    external-dns manages your Cloudflare zone (soyspray.vip).
    cert-manager issues certificates with DNS-01.

From then on, everything just works:

    Tailscale Operator supplies an IP.
    external-dns publishes that IP to your domain.
    cert-manager auto-issues TLS certificates.
    You connect over Tailscale from anywhere, securely, and the domain always has the correct record.

You should no longer need to do any manual fiddling with NextDNS rewrites or pinned ephemeral IPs. Whenever the Tailscale LB IP changes (rarely), external-dns catches the new IP and updates Cloudflare automatically. That is exactly the “idempotent” setup that Mattia’s article describes.
Good luck!

Feel free to tweak the approach depending on your specific homelab environment, but this pattern—Tailscale LB → external-dns → Cloudflare + cert-manager for DNS-01—provides you with a stable, zero-maintenance setup.
