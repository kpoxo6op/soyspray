# Autism traits assessment

This package serves the committed Vite bundle at
`https://autism.soyspray.vip`.

## Build and verify

Build the bundle before you commit deployment changes:

```bash
cd kubernetes/autism-traits/app
npm ci
npm run check
npx playwright install chromium
npm run test:e2e
```

Kustomize puts the bundle in content-hashed ConfigMaps. Four ConfigMaps hold
the ten WebP images. Each rendered object stays below the repository's
800 KiB safety threshold. The pod projects all site files into read-only
`/site` paths.

Render the Kubernetes package from the repository root:

```bash
kubectl kustomize kubernetes/autism-traits
```

## Deploy or park

The deployment command runs the existing `make go` preflight. Use the topic
branch name until the changes merge:

```bash
make autism-traits AUTISM_TRAITS_REVISION=feat/autism-trait-assessment
```

After merge, use `HEAD`. To remove the Argo CD Application and its managed
resources safely, set the role switch to `false`:

```bash
make autism-traits AUTISM_TRAITS_ENABLED=false
```

Set `AUTISM_TRAITS_ENABLED=true` to restore the site. Argo CD then prunes drift
and repairs changed resources automatically.

Verify the Argo CD state and the public response:

```bash
argocd app get autism-traits --grpc-web
curl --fail --head https://autism.soyspray.vip
```

To roll back, reconcile a known-good commit SHA through the same target:

```bash
make autism-traits AUTISM_TRAITS_REVISION=<known-good-commit>
```
