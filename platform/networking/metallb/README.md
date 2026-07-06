# MetalLB Prerequisite

MetalLB gives the home lab Kubernetes `LoadBalancer` behaviour similar to a
cloud cluster. It will be useful later when Kong needs internal and external
gateway service addresses.

Goal 001 only defines the prerequisite structure. It does not install MetalLB
or create a Kong service.

## Address Pool

`ip-address-pool.example.yaml` uses an example RFC1918 range and the annotation
`banklab.konghq.com/example-only: "true"`. Replace it with a safe unused LAN
range before applying to a real cluster.

Do not use your DHCP range. Reserve addresses on the router first.

## Validation

Local validation parses the YAML and renders the kustomization. Cluster
validation is opt-in and should happen only after the user chooses to apply the
prerequisites.

## Rollback

Rollback should remove the Git change and sync Argo CD, or manually delete the
MetalLB example resources if they were applied during a controlled test.

